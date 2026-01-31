"""
Módulo principal do sistema de computacao em grid.
Contém o ponto de entrada e a lógica principal do programa.
"""

from subprocess import call
from socket import socket, AF_INET, SOCK_DGRAM, SOCK_STREAM
import threading
import time
import os
import sys

from job import Job
from definicoes import PORTA_UDP, PORTA_UDP_PAR, PORTA_TCP, PORTA_TCP_PAR
from util import exibir_ajuda_geral_de_comandos

meu_socket_udp = socket(AF_INET, SOCK_DGRAM) # IPv4 e UDP
meu_socket_udp.settimeout(3)
meu_socket_udp.bind(('', PORTA_UDP))

MAX_DE_PARES = 3
lista_pares = []

job = None

#----------------------------------------------------------------------------------------
def encerrar_programa():
    """
    Encerra o programa de forma ordenada.
    """
    print('')
    print('\nParando o programa.')
    for par in lista_pares:
        meu_socket_udp.sendto('disconect', par)
    meu_socket_udp.close()
    sys.exit(0)
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def processa_pacote(msg_com_dados, endereco_par):
    """
    Processa um pacote UDP recebido de um par.
    """
    msg = msg_com_dados.decode('utf-8').split(';')  # Decode bytes to string
    resposta = 'void'
    if msg[0] == 'ok':
        if msg[1] == 'contact':
            if len(lista_pares) < MAX_DE_PARES:
                if endereco_par not in lista_pares:
                    lista_pares.append(endereco_par)
                    print(f'\nNosso pedido de contato foi aceito por {str(endereco_par)}')
            else:
                resposta = 'disconect'
    elif msg[0] == 'conect':
        if len(lista_pares) < MAX_DE_PARES:
            if endereco_par not in lista_pares:
                lista_pares.append(endereco_par)
            resposta = 'ok;contact'
            print(f'\nPedido de contato aceito originado de {str(endereco_par)}')
        else:
            resposta = 'not'
    elif msg[0] == 'disconect':
        if endereco_par in lista_pares:
            lista_pares.remove(endereco_par)
            print(f'Contato desfeito por solicitacao de {str(endereco_par)}')
    elif endereco_par in lista_pares:
        if msg[0] == 'do':
            resposta = 'what?'
            if len(msg) > 3:
                if msg[1] == 'cmd':
                    try:
                        call(['./programs/' + msg[2], msg[3]])
                        resposta = 'done cmd'
                    except Exception:  # Changed to catch all exceptions
                        resposta = 'erro cmd'
        elif msg[0] == 'msg':
            msg_print = 'Msg. de ' + str(endereco_par) + ' : '
            if len(msg) > 1:
                msg_print += msg[1]
            print('')
            print(msg_print)
            resposta = 'done'
    else:
        resposta = 'not'

    if resposta != 'void':
        meu_socket_udp.sendto(resposta.encode('utf-8'), endereco_par)  # Encode string to bytes
        #print('')
        #print('Enviei: ', resposta, '  Para: ', str(enderecoPar))
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def recepcao_thread():
    """
    Thread que aguarda a recepção de pacotes UDP e os envia para o devido processamento.
    """
    while True:
        try:
            msg_com_dados, endereco_par = meu_socket_udp.recvfrom(2048)
            threading.Thread(target=processa_pacote, args=(msg_com_dados, endereco_par)).start()
        except Exception as ex:
            print(ex)
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def contacta_pares():
    """
    Tenta contactar pares listados no arquivo 'peerlist'.
    """
    try:
        arquivo_pares = [line.strip() for line in open('peerlist')]
    except Exception as ex:
        print('Erro ao acessar o arquivo peerlist!')
        print(ex)
        return
    if len(arquivo_pares) == 0:
        print('Arquivo peerlist vazio!')
    elif len(lista_pares) < len(arquivo_pares) and len(lista_pares) < 3:
        for endereco_par in arquivo_pares:
            meu_socket_udp.sendto(b'conect', (endereco_par, PORTA_UDP_PAR))  # Send bytes
            print('\nTentando contactar a: ' + endereco_par)
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def enviar_arquivo(par, arquivo):
    """
    Transfere via TCP um arquivo para um par.
    """
    tcp_socket = socket(AF_INET, SOCK_STREAM)
    tcp_socket.connect((par[0], PORTA_TCP_PAR))
    file = open (arquivo, 'rb')
    buff = 1024
    arquivo = arquivo.replace('\\', '/')
    nome = arquivo.split('/')[-1]
    tamanho = os.path.getsize(arquivo)
    cabecalho = 'envio|' + nome + '|' + str(tamanho) + '|'

    # aqui preenchemos o cabecalho com esp. em branco ate ele ficar com tam. do buffer
    # isto e, o cabecalho deve ter buff bytes de tamanho (wrkrnd)
    cabecalho += ' ' * (1024 - len(cabecalho))

    print('ENVIANDO: ', arquivo, ' de ', tamanho)

    tcp_socket.send(cabecalho)

    dados = file.read(buff)
    while dados:
        tcp_socket.send(dados)
        dados = file.read(buff)

    tcp_socket.close()
    file.close()
    print('FIM DO ENVIO DE: ', arquivo)
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def prepara_job_no_par(par):
    """
    Prepara um par para receber o job carregado.
    """
    global job
    tcp_socket = socket(AF_INET, SOCK_STREAM)
    tcp_socket.connect((par[0], PORTA_TCP_PAR))
    tcp_socket.sendall(f'job|{job.diretorio}|'.encode('utf-8'))
    buff = 1024
    print('')
    resp = tcp_socket.recv(buff).decode('utf-8')
    if resp == 'ok':
        print(f'PAR {par[0]} esta preparado para o job {job.nome}')
        job.insere_par(par)
    else:
        print(f'PAR {par[0]} nao pode preparar (ou nao e possivel confirmar) para o job {job.nome}')
        job.remove_par(par)
    tcp_socket.close()
#----------------------------------------------------------------------------------------

#-Transfere via TCP um arquivo de entrada para um par------------------------------------
def envia_entrada(entrada, par):
    """
    Transfere via TCP um arquivo de entrada para um par.
    """
    file = None
    arquivo = './jobs/' + job.diretorio + '/entrada/' + entrada

    try:
        file = open(arquivo, 'rb')
    except Exception as ex:
        print('ERRO ao acessar o arquivo de entrada ', arquivo)
        print(ex)
        return False

    tamanho = os.path.getsize(arquivo)
    buff = 1024
    tcp_socket = socket(AF_INET, SOCK_STREAM)
    cabecalho = 'entrada|' + job.diretorio + '|' + entrada + '|' + str(tamanho) + '|' # entrada|diretorio_job|nome_entrada|tamanho|

    # aqui preenchemos o cabecalho com esp. em branco ate ele ficar com tam. do buffer
    # isto e, o cabecalho deve ter buff bytes de tamanho (wrkrnd)
    cabecalho += ' ' * (1024 - len(cabecalho))

    try:
        print('ENVIANDO ENTRADA: ', arquivo, ' de ', tamanho)
        tcp_socket.connect((par[0], PORTA_TCP_PAR))
        tcp_socket.send(cabecalho)
        dados = file.read(buff)
        while dados:
            tcp_socket.send(dados)
            dados = file.read(buff)
    except Exception as ex:
        print('\nHouve um erro na tranf. de um arquivo!')
        print(ex)
        tcp_socket.close()
        file.close()
        return False

    tcp_socket.close()
    file.close()

    print('FIM DO ENVIO DE: ', arquivo)
    return True
#----------------------------------------------------------------------------------------

#-Envia um comando para o par executar uma parte do job----------------------------------
def executa_parte_no_par(parte, par):
    """
    Envia um comando para o par executar uma parte do job.
    """
    tcp_socket = socket(AF_INET, SOCK_STREAM)

    # Formato: executa|programa|diretorio_job|nome_entrada|
    msg = 'executa|' + job.programa + '|' + job.diretorio + '|' + parte.entrada + '|'

    print('EXECUTANDO: ', job.programa, ' sobre a entrada ', parte.entrada, ' em ', par)

    tcp_socket.connect((par[0], PORTA_TCP_PAR))
    tcp_socket.send(msg)
    tcp_socket.close()
#----------------------------------------------------------------------------------------

#-Thread que cuida da divisao e execucao das partes do job nos pares---------------------
def job_thread():
    """
    Thread que cuida da divisao e execucao das partes do job nos pares.
    """
    global job

    if len(lista_pares) == 0:
        print('\nSem contato de pares para compartilhar o processamento.')
        return

    # esse loop tambem popula a lista job.listaPares com os pares prontos
    for par in lista_pares:
        prepara_job_no_par(par)

    if len(job.lista_pares) == 0:
        print('\nNenhum par ficou pronto para o processamento.')
        return

    while not job.finalizado():
        if job.possui_par_livre():
            for parte in job.lista_partes:
                print(parte.estado, parte.entrada)
                if parte.is_branco():
                    par_livre = job.proximo_par_livre()
                    if par_livre is None:
                        break
                    if not envia_entrada(parte.entrada, par_livre):
                        break
                    job.atribui_parte_ao_par(parte, par_livre)
                    executa_parte_no_par(parte, par_livre)
        time.sleep(0.7) # Estimar com experimentos qual o melhor valor...

    print('\nSUCESSO. O job foi concluido.')
#----------------------------------------------------------------------------------------

#-Inicia a execucao do job---------------------------------------------------------------
def executa_job():
    """
    Inicia a execucao do job carregado na memoria.
    """
    global job

    if not job:
        print('\nNenhum job carregado.')
        return
    if len(job.lista_partes) == 0:
        print('\nJob sem tarefas.')
        return
    if job.finalizado():
        print(f'\nTodas as tarefas do job \'{job.nome}\' foram completas.')
        return

    for parte in job.lista_partes:
        if parte.is_branco():
            print('PARTE: ', parte.entrada, ' EM BRANCO')

    threading.Thread(target=job_thread, args=()).start()
#----------------------------------------------------------------------------------------

#-Carrega para a memoria o job descrito pelo arquivo-------------------------------------
def carrega_job(nome_arquivo):
    """
    Carrega um job a partir do arquivo especificado.
    """
    global job
    arquivo_job = []

    try:
        for line in open('jobs/' + nome_arquivo):
            entrada = line.strip()
            if len(entrada) > 0:
                if entrada[0] != '#':
                    arquivo_job.append(entrada)
    except Exception as ex:
        print(f'Erro ao acessar o arquivo de job: {nome_arquivo}')
        print(ex)
        return

    if len(arquivo_job) == 0:
        print(f'Arquivo de job {nome_arquivo} está vazio.')
        return

    if len(arquivo_job) < 3:
        print(f'Arquivo de job {nome_arquivo} faltando parâmetros.')
        return

    job = Job(arquivo_job[0], arquivo_job[1], arquivo_job[2], nome_arquivo)
#----------------------------------------------------------------------------------------

#-Interpretacao dos comandos do prompt---------------------------------------------------
def trata_comando(string_comando):
    """
    Interpreta e executa os comandos digitados no prompt.
    """
    if len(string_comando) == 0:
        return

    comando = string_comando.split(' ')

    if comando[0] == 'ajuda':
        exibir_ajuda_geral_de_comandos()
    elif comando[0] == 'contato':
        contacta_pares()
    elif comando[0] == 'mensagem':
        if len(comando) < 3:
            print('\nArgumentos incorretos no comando.')
        else:
            try:
                id_par = int(comando[1])
            except ValueError:
                print('\nArgumentos incorretos no comando. Id do par deve ser numero.')
                return
            envia_mensagem(id_par, comando[2:])
    elif comando[0] == 'enviar':
        if len(comando) < 3:
            print('\nArgumentos incorretos no comando.')
        else:
            try:
                id_par = int(comando[1])
            except ValueError:
                print('\nArgumentos incorretos no comando. Id do par deve ser numero.')
                return
            if id_par < 0 or id_par+1 > len(lista_pares):
                print('\nNao temos este par na nossa lista.')
            enviar_arquivo(lista_pares[id_par], comando[2])
    elif comando[0] == 'pares':
        i = 0
        for par in lista_pares:
            print('#', i, ' - ', str(par), ' - Ocup.:', job.is_par_ocupado(par) if job is not None else False)
            i = i + 1
        if i == 0:
            print('Sem pares contactados.')
    elif comando[0] == 'carrega':
        if len(comando) < 2:
            print('\nArgumentos incorretos. Especifique o arquivo do job.')
            return
        carrega_job(comando[1])
    elif comando[0] == 'estado':
        if job is None:
            print('Sem job carregado.')
        else:
            job.print_status()
    elif comando[0] == 'executa':
        executa_job()
    elif comando[0] == 'sair':
        encerrar_programa()
    else:
        print('Comando nao reconhecido.')
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def envia_mensagem(id_par : int, textos : list):
    """
    Envia uma mensagem de texto, via UDP, para um par com determinado id.
    """
    if id_par < 0 or id_par+1 > len(lista_pares):
        print('\nNao temos este par na nossa lista.')
        return
    mensagem = 'msg:' + ' '.join(textos)
    meu_socket_udp.sendto(mensagem.encode('utf-8'), id_par)
#----------------------------------------------------------------------------------------

#-Transf. via TCP, o result. do process. e arquivo de saida (se houver) para um par------
def envia_saida(diretorio, saida, par):
    """
    Transfere via TCP resultados sobre o processamento e o arquivo de saida (caso haja)
    gerado por um job para um determinado par.
    """
    file = None

    arquivo = './temp/' + diretorio + '/saida/' + saida

    try:
        file = open(arquivo, 'rb')
    except Exception as ex:
        print(f'\nERRO ao acessar o arquivo de saida {arquivo}')
        print(ex)
        return False

    tamanho = os.path.getsize(arquivo)
    buff = 1024
    tcp_socket = socket(AF_INET, SOCK_STREAM)
    cabecalho = 'saida|' + diretorio + '|' + saida + '|' + str(tamanho) + '|' # saida|diretorio_job|nome_saida|tamanho|

    # aqui preenchemos o cabecalho com esp. em branco ate ele ficar com tam. do buffer
    # isto e, o cabecalho deve ter buff bytes de tamanho (wrkrnd)
    cabecalho += ' ' * (1024 - len(cabecalho))

    print(f'\nENVIANDO SAIDA: {arquivo} de {tamanho}')

    tcp_socket.connect((par[0], PORTA_TCP_PAR))

    try:
        tcp_socket.send(cabecalho)
        dados = file.read(buff)
        while dados:
            tcp_socket.send(dados)
            dados = file.read(buff)
    except Exception as ex:
        print('\nHouve um erro na transf. de um arquivo!')
        print(ex)
        tcp_socket.close()
        file.close()
        return False

    tcp_socket.close()
    file.close()

    print(f'\nFIM DO ENVIO DE: {arquivo}')
    return True
#----------------------------------------------------------------------------------------

#-Thread da conexao criada numa interacao com um par-------------------------------------
def conexao_tcp_thread(con, par):
    """
    Thread que cuida de uma conexao TCP com um par.
    """
    global job
    buff = 1024

    resp = con.recv(buff)
    #print ''
    #print 'TCP>', r[:200] ####### DBG

    cabecalho = resp.split('|')
    comando = cabecalho[0]

    if comando == 'envio':
        nome = cabecalho[1]
        tamanho = int(cabecalho[2])
        file = open('./recebidos/' + nome, 'wb+')
        recebidos = 0
        while recebidos < tamanho:
            resp = con.recv(buff)
            while resp:
                recebidos += len(resp)
                file.write(resp)
                resp = con.recv(buff)
            if not resp:
                break
        print('\nFECHANDO ARQUVIO', '- RECEBIDOS: ', recebidos)
        file.close()
    elif comando == 'job':
        diretorio_job = './temp/' + cabecalho[1]
        resultado = ''

        try:
            if os.path.isdir(diretorio_job):
                resultado = 'ok'
            else:
                os.makedirs(diretorio_job + '/entrada')
                os.makedirs(diretorio_job + '/saida')
                resultado = 'ok'
        except Exception as ex:
            resultado = 'erro'
            print(ex)

        con.send(resultado)
    elif comando == 'entrada':
        diretorio_entrada = './temp/' + cabecalho[1] + '/entrada/'
        nome_entrada = cabecalho[2]
        tamanho = int(cabecalho[3])
        file = open(diretorio_entrada + nome_entrada, 'wb+')
        recebidos = 0
        while recebidos < tamanho:
            resp = con.recv(buff)
            while resp:
                recebidos += len(resp)
                file.write(resp)
                resp = con.recv(buff)
            if not resp:
                break

        print('\nFECHANDO ARQUIVO: ', diretorio_entrada + nome_entrada, ' - RECEBIDOS: ', recebidos, ' de ', tamanho)
        file.close()
    elif comando == 'saida':   # Formato: saida|diretorio_job|nome_saida|tamanho|
        nome_diretorio = cabecalho[1]
        diretorio_saida = './jobs/' + nome_diretorio + '/saida/'
        nome_saida = cabecalho[2]
        tamanho = int(cabecalho[3])
        file = open(diretorio_saida + nome_saida, 'wb+')
        recebidos = 0
        while recebidos < tamanho:
            resp = con.recv(buff)
            while resp:
                recebidos += len(resp)
                file.write(resp)
                resp = con.recv(buff)
            if not resp:
                break

        print('\nFECHANDO ARQUIVO ', diretorio_saida + nome_saida, ' - RECEBIDOS: ', recebidos, ' de ', tamanho)
        file.close()

        # esta parte eh muito importante, nela mudamos o estado de uma tarefa concorrentemente
        if job.diretorio == nome_diretorio:
            job.finaliza_parte(nome_saida, par)
    elif comando == 'executa':  # Formato da msg: executa|programa|diretorio_job|nome_entrada|remetente
        programa = cabecalho[1]
        nome_diretorio_job = cabecalho[2]
        diretorio_entrada = './temp/' + nome_diretorio_job + '/entrada/'
        diretorio_saida = './temp/' + nome_diretorio_job + '/saida/'
        nome_entrada = cabecalho[3]
        nome_saida = nome_entrada[0:-3] + '.out'
        try:
            print(f'\nIniciando execucao do programa {programa}')
            call(['./programs/' + programa, diretorio_entrada + nome_entrada, diretorio_saida + nome_saida])
            resposta = 'pronto'
        except Exception as ex:
            print(f'\nERRO na execucao do programa {programa}')
            print(ex)
            resposta = 'erro'
        envia_saida(nome_diretorio_job, nome_saida, par)
    else:
        while resp:
            resp = con.recv(buff)

    con.close()
#----------------------------------------------------------------------------------------

#-Thread do socket de boas-vindas do tcp-------------------------------------------------
def tcp_thread():
    """
    Thread que aguarda conexoes TCP de pares.
    """
    sock = socket(AF_INET, SOCK_STREAM)
    sock.bind(('', PORTA_TCP))
    sock.listen(10)
    while True:
        con, par = sock.accept()
        threading.Thread(target=conexao_tcp_thread, args=tuple([con, par])).start()
#----------------------------------------------------------------------------------------

#-Inicializacao das threads--------------------------------------------------------------
try:
    threading.Thread(target=tcp_thread, args=()).start()
    threading.Thread(target=recepcao_thread, args=()).start()
except Exception as ex:
    print('Problemas com uma thread.')
    print(ex)
    meu_socket_udp.close()
    sys.exit(1)

print('Pronto.')
print('')
#----------------------------------------------------------------------------------------

#-Loop principal, usado para entrada de comandos-----------------------------------------
while True:
    try:
        str_comando = input('Comando: ')
        trata_comando(str_comando)
    except KeyboardInterrupt:
        encerrar_programa()
    except Exception as ex:
        print('\nHouve um erro!')
        print(ex)
#----------------------------------------------------------------------------------------
