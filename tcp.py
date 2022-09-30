import asyncio, random
from tcputils import *


class Servidor:
    def __init__(self, rede, porta):
        self.rede = rede
        self.porta = porta
        self.conexoes = {}
        self.callback = None
        self.rede.registrar_recebedor(self._rdt_rcv)

    def registrar_monitor_de_conexoes_aceitas(self, callback):
        """
        Usado pela camada de aplicação para registrar uma função para ser chamada
        sempre que uma nova conexão for aceita
        """
        self.callback = callback

    def _rdt_rcv(self, src_addr, dst_addr, segment):
        src_port, dst_port, seq_no, ack_no, \
            flags, window_size, checksum, urg_ptr = read_header(segment)

        if dst_port != self.porta:
            # Ignora segmentos que não são destinados à porta do nosso servidor
            return
        if not self.rede.ignore_checksum and calc_checksum(segment, src_addr, dst_addr) != 0:
            print('descartando segmento com checksum incorreto')
            return

        payload = segment[4*(flags >> 12):]
        id_conexao = (src_addr, src_port, dst_addr, dst_port)

        if (flags & FLAGS_SYN) == FLAGS_SYN:
            # A flag SYN estar setada significa que é um cliente tentando estabelecer uma conexão nova
            # TODO: talvez você precise passar mais coisas para o construtor de conexão
            conexao = self.conexoes[id_conexao] = Conexao(self, id_conexao, ack_no, seq_no+1)
            conexao.own_ack_no = seq_no + 1
            # TODO: você precisa fazer o handshake aceitando a conexão. Escolha se você acha melhor
            # fazer aqui mesmo ou dentro da classe Conexao.
            self.rede.enviar(fix_checksum(make_header(dst_port, src_port, conexao.own_seq_no, conexao.own_ack_no, FLAGS_SYN | FLAGS_ACK), dst_addr, src_addr), src_addr)
            conexao.own_seq_no += 1
            if self.callback:
                self.callback(conexao)
        elif id_conexao in self.conexoes:
            # Passa para a conexão adequada se ela já estiver estabelecida
            self.conexoes[id_conexao]._rdt_rcv(seq_no, ack_no, flags, payload)
        else:
            print('%s:%d -> %s:%d (pacote associado a conexão desconhecida)' %
                  (src_addr, src_port, dst_addr, dst_port))


class Conexao:
    def __init__(self, servidor, id_conexao, ack_no=0, recieved_seq_no=0):
        self.servidor = servidor
        self.id_conexao = id_conexao
        self.callback = None
        self.own_seq_no = random.randint(0, 0xffff)
        self.recieved_seq_no = recieved_seq_no
        self.own_ack_no = self.recieved_seq_no + 1
        self.recieved_ack_no = ack_no
        self.data_buffer = b''
        self.awaiting_ack = False
        self.timer = asyncio.get_event_loop().call_later(1, self._exemplo_timer)  # um timer pode ser criado assim; esta linha é só um exemplo e pode ser removida
        #self.timer.cancel()   # é possível cancelar o timer chamando esse método; esta linha é só um exemplo e pode ser removida

    def _exemplo_timer(self):
        # Esta função é só um exemplo e pode ser removida
        print('Este é um exemplo de como fazer um timer')

    def _rdt_rcv(self, seq_no, ack_no, flags, payload):
        # TODO: trate aqui o recebimento de segmentos provenientes da camada de rede.
        # Chame self.callback(self, dados) para passar dados para a camada de aplicação após
        # garantir que eles não sejam duplicados e que tenham sido recebidos em ordem.

        print("recieved_seq_no: %d" % seq_no)
        print("own_ack_no: %d" % self.own_ack_no)
        print("own_seq_no: %d" % self.recieved_seq_no)
        print("recieved_seq_no2: %d" % (self.recieved_seq_no + len(payload)))
        if FLAGS_FIN == (flags & FLAGS_FIN):
            print("Fechamento de conexão")
            self.own_ack_no += 1
            self.callback(self, b"")
            self.servidor.rede.enviar(
                fix_checksum(make_header(self.id_conexao[3], self.id_conexao[1], self.own_seq_no, self.own_ack_no, FLAGS_ACK),
                                self.id_conexao[2], self.id_conexao[0]), self.id_conexao[0])


        if FLAGS_ACK == (flags & FLAGS_ACK) and len(payload) != 0:
            if seq_no == self.own_ack_no:
                self.recieved_seq_no = seq_no
                print("recebido segmento com seq_no correto")
                self.callback(self, payload)
                self.own_ack_no = seq_no + len(payload)
                self.recieved_ack_no = ack_no
                payload = b""
                self.servidor.rede.enviar(fix_checksum(make_header(self.id_conexao[3], self.id_conexao[1], self.own_seq_no, self.own_ack_no, FLAGS_ACK) + payload, self.id_conexao[2], self.id_conexao[0]), self.id_conexao[0])

            else:
                print("recebido segmento com seq_no errado")
        #print('recebido payload: %r' % payload)

    # Os métodos abaixo fazem parte da API

    def registrar_recebedor(self, callback):
        """
        Usado pela camada de aplicação para registrar uma função para ser chamada
        sempre que dados forem corretamente recebidos
        """
        self.callback = callback

    def enviar(self, dados):
        """
        Usado pela camada de aplicação para enviar dados
        """

        # TODO: implemente aqui o envio de dados.
        # Chame self.servidor.rede.enviar(segmento, dest_addr) para enviar o segmento
        # que você construir para a camada de rede.

        self.data_buffer += dados

        while len(self.data_buffer) > 0:
            payload = self.data_buffer[:MSS]
            self.data_buffer = self.data_buffer[MSS:]
            self.servidor.rede.enviar(fix_checksum(make_header(self.id_conexao[3], self.id_conexao[1], self.own_seq_no, self.own_ack_no, FLAGS_ACK) + payload, self.id_conexao[2], self.id_conexao[0]), self.id_conexao[0])
            self.own_seq_no += len(payload)




    def fechar(self):
        """
        Usado pela camada de aplicação para fechar a conexão
        """
        # TODO: implemente aqui o fechamento de conexão
        self.servidor.rede.enviar(
            fix_checksum(make_header(self.id_conexao[3], self.id_conexao[1], self.own_seq_no, self.own_ack_no, FLAGS_FIN),
                         self.id_conexao[2], self.id_conexao[0]), self.id_conexao[0])
        del self.servidor.conexoes[self.id_conexao]