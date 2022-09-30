#!/usr/bin/env python3
#T1
import asyncio
from readline import append_history_file
from tcp import Servidor
import re

quebra = b''
apelidos_em_uso = []
usuarios_conectados = []
canais = []
usuarios_canais = []


def validar_nome(nome):
    return re.match(br'^[a-zA-Z][a-zA-Z0-9_-]*$', nome) is not None



def sair(conexao):
    global quebra, apelidos_em_uso, usuarios_conectados, canais, usuarios_canais

    apelido = apelidos_em_uso[usuarios_conectados.index(conexao)]

    for usuario in usuarios_canais:
        if conexao in usuario:
            for unidade in usuario:
                unidade.enviar(b':' + apelido + b' QUIT : Connection closed\r\n')
            usuario.remove(conexao)

    apelidos_em_uso.pop(usuarios_conectados.index(conexao))
    usuarios_conectados.remove(conexao)
    print(conexao, 'conexão fechada')
    conexao.fechar()



def get_index(objeto, index):
    cont = 0
    for item in index:
        if item.lower() == objeto.lower():
            return cont
        cont += 1
    
    return -1



def lista_usuarios(conexao, canal):
    global quebra, apelidos_em_uso, usuarios_conectados, canais, usuarios_canais
    
    index = get_index(canal, canais)
    apelido = apelidos_em_uso[usuarios_conectados.index(conexao)]
    lista_usuarios = []

    for usuario in usuarios_canais[index]:
        lista_usuarios.append(apelidos_em_uso[usuarios_conectados.index(usuario)])
    lista_usuarios.sort()

    quebra_de_linha = 1
    for usuario in lista_usuarios:
        if quebra_de_linha == 1:
            mensagem = b':server 353 ' + apelido + b' = ' + canal + b' :'
            if len(mensagem) + len(usuario) + 2 <= 512:
                mensagem += usuario
            quebra_de_linha = 0
        else:
            if len(mensagem) + len(usuario) + 3 <= 512:
                mensagem += b' ' + usuario
            else:
                mensagem += b'\r\n'
                conexao.enviar(mensagem)
                quebra_de_linha = 1
            
    conexao.enviar(mensagem + b'\r\n')
    conexao.enviar(b':server 366 ' + apelido + b' ' + canal + b' :End of /NAMES list.\r\n')



def nick(conexao, comando):
    global quebra, apelidos_em_uso, usuarios_conectados, canais, usuarios_canais

    comando_split = comando.split(b' ')
    apelido_desejado = comando_split[1].split(b'\r\n')[0]

    if validar_nome(apelido_desejado):
        if apelido_desejado.lower() not in apelidos_em_uso:
            if apelidos_em_uso[usuarios_conectados.index(conexao)] == b'*':
                conexao.enviar(b':server 001 ' + apelido_desejado + b' :Welcome\r\n') 
                conexao.enviar(b':server 422 ' + apelido_desejado + b' :MOTD File is missing\r\n')
            else:
                conexao.enviar(b':' + apelidos_em_uso[usuarios_conectados.index(conexao)] + b' NICK ' + apelido_desejado + b'\r\n')
                print(apelido_desejado) 
            apelidos_em_uso[usuarios_conectados.index(conexao)] = apelido_desejado
        else:
            conexao.enviar(b':server 433 ' + apelidos_em_uso[usuarios_conectados.index(conexao)] + b' ' + apelido_desejado + b' :Nickname is already in use\r\n')
    else:
        conexao.enviar(b':server 432 ' + apelidos_em_uso[usuarios_conectados.index(conexao)] + b' ' + apelido_desejado + b' :Erroneous nickname\r\n')



def privmsg(conexao, comando):
    global quebra, apelidos_em_uso, usuarios_conectados, canais, usuarios_canais

    destinatario = comando.split(b' ')[1]
    destinatario = destinatario.lower()
    mensagem = comando.split(b':')[1].split(b'\r\n')[0]

    if destinatario.startswith(b'#'):
        for pessoa in usuarios_canais[get_index(destinatario, canais)]:
            if pessoa != conexao:
                pessoa.enviar(b':' + apelidos_em_uso[usuarios_conectados.index(conexao)] + b' PRIVMSG ' + destinatario + b' :' + mensagem + b'\r\n')
    else:
        if destinatario in apelidos_em_uso:
            pos_destino = usuarios_conectados[get_index(destinatario, apelidos_em_uso)]
            pos_destino.enviar(b':' + apelidos_em_uso[usuarios_conectados.index(conexao)] + b' PRIVMSG ' + destinatario + b' :' + mensagem + b'\r\n')



def join(conexao, comando):
    global quebra, apelidos_em_uso, usuarios_conectados, canais, usuarios_canais

    canal = comando.split(b' ')[1].split(b'\r\n')[0]
    if canal.startswith(b'#'):
        if canal not in canais:
            canais.append(canal)
            usuarios_canais.append([])

        usuarios_canais[canais.index(canal)].append(conexao)
        for usuario in usuarios_canais[canais.index(canal)]:
            usuario.enviar(b':' + apelidos_em_uso[usuarios_conectados.index(conexao)] + b' JOIN :' + canal + b'\r\n')

    lista_usuarios(conexao, canal)




def part(conexao, comando):
    global quebra, apelidos_em_uso, usuarios_conectados, canais, usuarios_canais

    canal = comando.split(b' ')[1].split(b'\r\n')[0] 
    if canal.startswith(b'#'): 
        if (get_index(canal, canais) != -1): 
            for usuario in usuarios_canais[get_index(canal, canais)]: 
                usuario.enviar(b':' + apelidos_em_uso[usuarios_conectados.index(conexao)] + b' PART ' + canal + b'\r\n')
            
            usuarios_canais[get_index(canal, canais)].remove(conexao)
    



def dados_recebidos(conexao, dados):
    global quebra, apelidos_em_uso, usuarios_conectados, canais, usuarios_canais

    if dados == b'':
        return sair(conexao)

    comandos = dados.splitlines(True)

    for comando in comandos:

        if comando.startswith(b'PING') and comando.endswith(b'\r\n'):
            conexao.enviar(b':server PONG server :' + comando.split(b' ', 1)[1])

        elif comando.startswith(b'NICK') and comando.endswith(b'\r\n'):
            nick(conexao, comando)
        
        elif comando.startswith(b'PRIVMSG') and comando.endswith(b'\r\n'):
            privmsg(conexao, comando)
        
        elif comando.startswith(b'JOIN') and comando.endswith(b'\r\n'):
            join(conexao, comando)

        elif comando.startswith(b'PART') and comando.endswith(b'\r\n'):
            part(conexao, comando)

        else:

            quebra = quebra + comando

            if quebra.startswith(b'PING') and quebra.endswith(b'\r\n'):
                conexao.enviar(b':server PONG server :' + quebra.split(b' ', 1)[1])
                quebra = b''

            elif quebra.startswith(b'NICK') and quebra.endswith(b'\r\n'):
                nick(conexao, quebra)
                quebra = b''
            
            elif quebra.startswith(b'PRIVMSG') and quebra.endswith(b'\r\n'):
                privmsg(conexao, quebra)
                quebra = b''
            
            elif quebra.startswith(b'JOIN') and quebra.endswith(b'\r\n'):
                join(conexao, quebra)
                quebra = b''

            elif quebra.startswith(b'PART') and quebra.endswith(b'\r\n'):
                part(conexao, quebra)
                quebra = b''
        
    print(conexao, dados)



def conexao_aceita(conexao):
    global quebra, apelidos_em_uso, usuarios_conectados, canais, usuarios_canais

    print(conexao, 'nova conexão')
    usuarios_conectados.append(conexao)
    apelidos_em_uso.append(b'*')
    conexao.registrar_recebedor(dados_recebidos)


servidor = Servidor(6667)
servidor.registrar_monitor_de_conexoes_aceitas(conexao_aceita)
asyncio.get_event_loop().run_forever()
