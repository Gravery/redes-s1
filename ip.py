from iputils import *

class IP:
    def __init__(self, enlace):
        """
        Inicia a camada de rede. Recebe como argumento uma implementação
        de camada de enlace capaz de localizar os next_hop (por exemplo,
        Ethernet com ARP).
        """
        self.callback = None
        self.enlace = enlace
        self.enlace.registrar_recebedor(self.__raw_recv)
        self.ignore_checksum = self.enlace.ignore_checksum
        self.meu_endereco = None
        self.hops = []
        self.cidr = []

    def __raw_recv(self, datagrama):
        dscp, ecn, identification, flags, frag_offset, ttl, proto, \
           src_addr, dst_addr, payload = read_ipv4_header(datagrama)
        if dst_addr == self.meu_endereco:
            # atua como host
            if proto == IPPROTO_TCP and self.callback:
                self.callback(src_addr, dst_addr, payload)
        else:
            # atua como roteador
            next_hop = self._next_hop(dst_addr)

            # TODO: Trate corretamente o campo TTL do datagrama
        
            #Descarte de datagrama com o fim do ttl
            if ttl == 1:
                payload_ttl1 = struct.pack('!BBHI', 11, 0, 0, 0) + datagrama[:28]
                checksum = calc_checksum(payload_ttl1)
                payload_ttl1 = struct.pack('!BBHI', 11, 0, checksum, 0) + datagrama[:28]
                self.enviar(payload_ttl1, src_addr, IPPROTO_ICMP)
                return -1
            #Redução do ttl
            else:
                ttl -= 1

            src = str2addr(src_addr)
            dst = str2addr(dst_addr)

            hdr = struct.pack('!BBHHHBBH', 69, 0, 20 + len(payload), 0, (0 << 13)|0, ttl, proto, 0) + src + dst
            checksum = calc_checksum(hdr)
            hdr = struct.pack('!BBHHHBBH', 69, 0, 20 + len(payload), 0, (0 << 13)|0, ttl, proto, checksum) + src + dst
            datagrama = hdr + payload

            self.enlace.enviar(datagrama, next_hop)

    def _next_hop(self, dest_addr):
        # TODO: Use a tabela de encaminhamento para determinar o próximo salto
        # (next_hop) a partir do endereço de destino do datagrama (dest_addr).
        # Retorne o next_hop para o dest_addr fornecido.
        addr, = struct.unpack('!I', str2addr(dest_addr))
        next_hop = None
        maior = -1

        #Realza uma varredura em todos os valores da tabela para definir o next_hop
        for cidr, hop in self.tabela:
            split = cidr.split('/')
            cidr = split[0]
            nbits = int(split[1])
            addr_cidr = str2addr(cidr)
            addr2, = struct.unpack('!I', addr_cidr)

            #Desempate entre os endereços para atribuir o valor de next_hop para o que possuir prefixo mais longo
            if (addr2 >> 32 - nbits << 32 - nbits) == (addr >> 32 - nbits << 32 - nbits):
                if (nbits > maior):
                    maior = nbits
                    next_hop = hop

        return next_hop
    

    def definir_endereco_host(self, meu_endereco):
        """
        Define qual o endereço IPv4 (string no formato x.y.z.w) deste host.
        Se recebermos datagramas destinados a outros endereços em vez desse,
        atuaremos como roteador em vez de atuar como host.
        """
        self.meu_endereco = meu_endereco

    def definir_tabela_encaminhamento(self, tabela):
        """
        Define a tabela de encaminhamento no formato
        [(cidr0, next_hop0), (cidr1, next_hop1), ...]

        Onde os CIDR são fornecidos no formato 'x.y.z.w/n', e os
        next_hop são fornecidos no formato 'x.y.z.w'.
        """
        # TODO: Guarde a tabela de encaminhamento. Se julgar conveniente,
        # converta-a em uma estrutura de dados mais eficiente.
        self.tabela = tabela
        self.cidr = []
        self.hops = []

        for cidr, hop in (tabela):
            if cidr not in self.cidr:
                self.cidr.append(cidr)
                self.hops.append(hop)
            else:
                self.hops[self.cidr.index(cidr)] = hop


    def registrar_recebedor(self, callback):
        """
        Registra uma função para ser chamada quando dados vierem da camada de rede
        """
        self.callback = callback

    def enviar(self, segmento, dest_addr, protocolo=IPPROTO_TCP):
        """
        Envia segmento para dest_addr, onde dest_addr é um endereço IPv4
        (string no formato x.y.z.w).
        """
        next_hop = self._next_hop(dest_addr)
        # TODO: Assumindo que a camada superior é o protocolo TCP, monte o
        # datagrama com o cabeçalho IP, contendo como payload o segmento.

        #Montagem do datagrama com checksum e adição do segmento a ser enviado
        addr_meu_endereco = str2addr(self.meu_endereco)
        addr_dest = str2addr(dest_addr)

        hdr = struct.pack('!BBHHHBBH',  69, 0, 20 + len(segmento), 0, (0 << 13) | 0, 64, protocolo, 0) + addr_meu_endereco + addr_dest
        checksum = calc_checksum(hdr)
        hdr = struct.pack('!BBHHHBBH',  69, 0, 20 + len(segmento), 0, (0 << 13) | 0, 64, protocolo, checksum) + addr_meu_endereco + addr_dest
        datagrama = hdr + segmento

        self.enlace.enviar(datagrama, next_hop)
