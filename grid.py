from subprocess import call
from socket import socket, AF_INET, SOCK_DGRAM, SOCK_STREAM
import threading
import time
import os
import sys

from Job import *
from Definicoes import *
from Util import *

meuSocket = socket(AF_INET, SOCK_DGRAM) # IPv4 e UDP
meuSocket.settimeout(3)
meuSocket.bind(('', porta))

maxDePares = 3
listaPares = []

job = None

#----------------------------------------------------------------------------------------
def encerrarPrograma():
    print('')
    print('\nParando o programa.')
    for par in listaPares:
        meuSocket.sendto('disconect', par)
    meuSocket.close()
    sys.exit(0)
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def processaPacote(msgComDados, enderecoPar):
    msg = msgComDados.decode('utf-8').split(';')  # Decode bytes to string
    resposta = 'void'
    if msg[0] == 'ok':
        if msg[1] == 'contact':
            if len(listaPares) < maxDePares:
                if enderecoPar not in listaPares:
                    listaPares.append(enderecoPar)
                    print(f'\nNosso pedido de contato foi aceito por {str(enderecoPar)}')
            else:
                resposta = 'disconect'
    elif msg[0] == 'conect':
        if len(listaPares) < maxDePares:
            if enderecoPar not in listaPares:
                listaPares.append(enderecoPar)
            resposta = 'ok;contact'
            print(f'\nPedido de contato aceito originado de {str(enderecoPar)}')
        else:
            resposta = 'not'
    elif msg[0] == 'disconect':
        if enderecoPar in listaPares:
            listaPares.remove(enderecoPar)
            print(f'Contato desfeito por solicitacao de {str(enderecoPar)}')
    elif enderecoPar in listaPares:
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
            msg_print = 'Msg. de ' + str(enderecoPar) + ' : '
            if len(msg) > 1:
                msg_print += msg[1]
            print('')
            print(msg_print)
            resposta = 'done'
    else:
        resposta = 'not'

    if resposta != 'void':
        meuSocket.sendto(resposta.encode('utf-8'), enderecoPar)  # Encode string to bytes
        #print('')
        #print('Enviei: ', resposta, '  Para: ', str(enderecoPar))
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def recepcaoThread():
    while True:
        try:
            msgComDados, enderecoPar = meuSocket.recvfrom(2048)
            threading.Thread(target=processaPacote, args=(msgComDados, enderecoPar)).start()
        except Exception as e:
            print(e)
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def contactaPares():
    try:
        arquivoPares = [line.strip() for line in open('peerlist')]
    except Exception as e:
        print('Erro ao acessar o arquivo peerlist!')
        print(e)
        return
    if len(arquivoPares) == 0:
        print('Arquivo peerlist vazio!')
    elif len(listaPares) < len(arquivoPares) and len(listaPares) < 3:
        for enderecoPar in arquivoPares:
            meuSocket.sendto(b'conect', (enderecoPar, portaPar))  # Send bytes
            print('\nTentando contactar a: ' + enderecoPar)
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def enviarArquivo(par, arquivo):
    tcpSocket = socket(AF_INET, SOCK_STREAM)
    tcpSocket.connect((par[0], PORTA_TCP_PAR))
    f = open (arquivo, 'rb')
    buff = 1024
    arquivo = arquivo.replace('\\', '/')
    nome = arquivo.split('/')[-1]
    tamanho = os.path.getsize(arquivo)
    cabecalho = 'envio|' + nome + '|' + str(tamanho) + '|'

    # aqui preenchemos o cabecalho com esp. em branco ate ele ficar com tam. do buffer
    # isto e, o cabecalho deve ter buff bytes de tamanho (wrkrnd)
    cabecalho += ' ' * (1024 - len(cabecalho))

    print('ENVIANDO: ', arquivo, ' de ', tamanho)

    tcpSocket.send(cabecalho)

    dados = f.read(buff)
    while (dados):
        tcpSocket.send(dados)
        dados = f.read(buff)

    tcpSocket.close()
    f.close()
    print('FIM DO ENVIO DE: ', arquivo)
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def preparaJobNoPar(par):
    global job
    tcpSocket = socket(AF_INET, SOCK_STREAM)
    tcpSocket.connect((par[0], PORTA_TCP_PAR))
    tcpSocket.sendall(f'job|{job.diretorio}|'.encode('utf-8'))
    buff = 1024
    print('')
    r = tcpSocket.recv(buff).decode('utf-8')
    if r == 'ok':
        print(f'PAR {par[0]} esta preparado para o job {job.nome}')
        job.inserePar(par)
    else:
        print(f'PAR {par[0]} nao pode preparar (ou nao e possivel confirmar) para o job {job.nome}')
        job.removePar(par)
    tcpSocket.close()
#----------------------------------------------------------------------------------------

#-Transfere via TCP um arquivo de entrada para um par------------------------------------
def enviaEntrada(entrada, par):
    f = None
    arquivo = './jobs/' + job.diretorio + '/entrada/' + entrada

    try:
        f = open(arquivo, 'rb')
    except Exception as e:
        print('ERRO ao acessar o arquivo de entrada ', arquivo)
        print(e)
        return False

    tamanho = os.path.getsize(arquivo)
    buff = 1024
    tcpSocket = socket(AF_INET, SOCK_STREAM)
    cabecalho = 'entrada|' + job.diretorio + '|' + entrada + '|' + str(tamanho) + '|' # entrada|diretorio_job|nome_entrada|tamanho|

    # aqui preenchemos o cabecalho com esp. em branco ate ele ficar com tam. do buffer
    # isto e, o cabecalho deve ter buff bytes de tamanho (wrkrnd)
    cabecalho += ' ' * (1024 - len(cabecalho))

    try:
        print('ENVIANDO ENTRADA: ', arquivo, ' de ', tamanho)
        tcpSocket.connect((par[0], PORTA_TCP_PAR))
        tcpSocket.send(cabecalho)
        dados = f.read(buff)
        while (dados):
            tcpSocket.send(dados)
            dados = f.read(buff)
    except Exception as e:
        print('\nHouve um erro na tranf. de um arquivo!')
        print(e)
        tcpSocket.close()
        f.close()
        return False

    tcpSocket.close()
    f.close()

    print('FIM DO ENVIO DE: ', arquivo)
    return True
#----------------------------------------------------------------------------------------

#-Envia um comando para o par executar uma parte do job----------------------------------
def executaParteNoPar(parte, par):
    tcpSocket = socket(AF_INET, SOCK_STREAM)

    # Formato: executa|programa|diretorio_job|nome_entrada|
    msg = 'executa|' + job.programa + '|' + job.diretorio + '|' + parte.entrada + '|'

    print('EXECUTANDO: ', job.programa, ' sobre a entrada ', parte.entrada, ' em ', par)

    tcpSocket.connect((par[0], PORTA_TCP_PAR))
    tcpSocket.send(msg)
    tcpSocket.close()
#----------------------------------------------------------------------------------------

#-Thread que cuida da divisao e execucao das partes do job nos pares---------------------
def jobThread():
    global job

    if len(listaPares) == 0:
        print('\nSem contato de pares para compartilhar o processamento.')
        return

    # esse loop tambem popula a lista job.listaPares com os pares prontos
    for par in listaPares:
        preparaJobNoPar(par)

    if len(job.listaPares) == 0:
        print('\nNenhum par ficou pronto para o processamento.')
        return

    while not job.finalizado():
        if job.possuiParLivre():
            for parte in job.listaPartes:
                print(parte.estado, parte.entrada)
                if parte.is_branco():
                    parLivre = job.proximoParLivre()
                    if parLivre is None:
                        break
                    if not enviaEntrada(parte.entrada, parLivre):
                        break
                    job.atribuiParteAoPar(parte, parLivre)
                    executaParteNoPar(parte, parLivre)
        time.sleep(0.7) # Estimar com experimentos qual o melhor valor...

    print('\nSUCESSO. O job foi concluido.')
#----------------------------------------------------------------------------------------

#-Inicia a execucao do job---------------------------------------------------------------
def executaJob():
    global job

    if not job:
        print('\nNenhum job carregado.')
        return
    if len(job.listaPartes) == 0:
        print('\nJob sem tarefas.')
        return
    if job.finalizado():
        print(f'\nTodas as tarefas do job \'{job.nome}\' foram completas.')
        return

    for parte in job.listaPartes:
        if parte.is_branco():
            print('PARTE: ', parte.entrada, ' EM BRANCO')

    threading.Thread(target=jobThread, args=()).start()
#----------------------------------------------------------------------------------------

#-Carrega para a memoria o job descrito pelo arquivo-------------------------------------
def carregaJob(nomeArquivo):
    global job
    arquivoJob = []

    try:
        for line in open('jobs/' + nomeArquivo):
            entrada = line.strip()
            if len(entrada) > 0:
                if entrada[0] != '#':
                    arquivoJob.append(entrada)
    except Exception as e:
        print(f'Erro ao acessar o arquivo de job: {nomeArquivo}')
        print(e)
        return

    if len(arquivoJob) == 0:
        print(f'Arquivo de job {nomeArquivo} está vazio.')
        return

    if len(arquivoJob) < 3:
        print(f'Arquivo de job {nomeArquivo} faltando parâmetros.')
        return

    job = Job(arquivoJob[0], arquivoJob[1], arquivoJob[2], nomeArquivo)
#----------------------------------------------------------------------------------------

#-Interpretacao dos comandos do prompt---------------------------------------------------
def trataComando(stringComando):
    if len(stringComando) == 0:
        return

    comando = stringComando.split(' ')

    if comando[0] == 'ajuda':
        exibirAjudaDeComandos()
    elif comando[0] == 'contato':
        contactaPares()
    elif comando[0] == 'mensagem':
        if len(comando) < 3:
            print('\nArgumentos incorretos no comando.')
        else:
            try:
                idPar = int(comando[1])
            except ValueError:
                print('\nArgumentos incorretos no comando. Id do par deve ser numero.')
                return

            if idPar < 0 or idPar+1 > len(listaPares):
                print('\nNao temos este par na nossa lista.')
            else:
                msgConteudo = ''
                for s in comando[2:]:
                    msgConteudo += s + ' '
                meuSocket.sendto('msg;' + msgConteudo, listaPares[idPar])
    elif comando[0] == 'enviar':
        if len(comando) < 3:
            print('\nArgumentos incorretos no comando.')
        else:
            try:
                idPar = int(comando[1])
            except ValueError:
                print('\nArgumentos incorretos no comando. Id do par deve ser numero.')
                return

            if idPar < 0 or idPar+1 > len(listaPares):
                print('\nNao temos este par na nossa lista.')

            enviarArquivo(listaPares[idPar], comando[2])
    elif comando[0] == 'pares':
        i = 0
        for par in listaPares:
            print('#', i, ' - ', str(par), ' - Ocup.:', job.isParOcupado(par) if job is not None else False)
            i = i + 1
        if i == 0:
            print('Sem pares contactados.')
    elif comando[0] == 'carrega':
        if len(comando) < 2:
            print('\nArgumentos incorretos. Especifique o arquivo do job.')
            return
        carregaJob(comando[1])
    elif comando[0] == 'estado':
        if job is None:
            print('Sem job carregado.')
        else:
            for parte in job.listaPartes:
                print('#', parte.entrada, '-', parte.estado)
    elif comando[0] == 'executa':
        executaJob()
    elif comando[0] == 'sair':
        encerrarPrograma()
    else:
        print('Comando nao reconhecido.')
#----------------------------------------------------------------------------------------

#-Transf. via TCP, o result. do process. e arquivo de saida (se houver) para um par------
def enviaSaida(dir, saida, par):
    f = None

    arquivo = './temp/' + dir + '/saida/' + saida

    try:
        f = open(arquivo, 'rb')
    except Exception as e:
        print(f'\nERRO ao acessar o arquivo de saida {arquivo}')
        print(e)
        return False

    tamanho = os.path.getsize(arquivo)
    buff = 1024
    tcpSocket = socket(AF_INET, SOCK_STREAM)
    cabecalho = 'saida|' + dir + '|' + saida + '|' + str(tamanho) + '|' # saida|diretorio_job|nome_saida|tamanho|

    # aqui preenchemos o cabecalho com esp. em branco ate ele ficar com tam. do buffer
    # isto e, o cabecalho deve ter buff bytes de tamanho (wrkrnd)
    cabecalho += ' ' * (1024 - len(cabecalho))

    print(f'\nENVIANDO SAIDA: {arquivo} de {tamanho}')

    tcpSocket.connect((par[0], PORTA_TCP_PAR))

    try:
        tcpSocket.send(cabecalho)
        dados = f.read(buff)
        while (dados):
            tcpSocket.send(dados)
            dados = f.read(buff)
    except Exception as e:
        print('\nHouve um erro na transf. de um arquivo!')
        print(e)
        tcpSocket.close()
        f.close()
        return False

    tcpSocket.close()
    f.close()

    print(f'\nFIM DO ENVIO DE: {arquivo}')
    return True
#----------------------------------------------------------------------------------------

#-Thread da conexao criada numa interacao com um par-------------------------------------
def conexaoTcpThread(con, par):
    global job
    buff = 1024

    r = con.recv(buff)
    #print ''
    #print 'TCP>', r[:200] ####### DBG

    cabecalho = r.split('|')
    comando = cabecalho[0]

    if comando == 'envio':
        nome = cabecalho[1]
        tamanho = int(cabecalho[2])
        f = open('./recebidos/' + nome, 'wb+')
        recebidos = 0
        while recebidos < tamanho:
            r = con.recv(buff)
            while (r):
                recebidos += len(r)
                f.write(r)
                r = con.recv(buff)
            if not r:
                break
        print('\nFECHANDO ARQUVIO', '- RECEBIDOS: ', recebidos)
        f.close()
    elif comando == 'job':
        diretorioJob = './temp/' + cabecalho[1]
        resultado = ''

        try:
            if os.path.isdir(diretorioJob):
                resultado = 'ok'
            else:
                os.makedirs(diretorioJob + '/entrada')
                os.makedirs(diretorioJob + '/saida')
                resultado = 'ok'
        except Exception as e:
            resultado = 'erro'
            print(e)

        con.send(resultado)
    elif comando == 'entrada':
        diretorioEntrada = './temp/' + cabecalho[1] + '/entrada/'
        nomeEntrada = cabecalho[2]
        tamanho = int(cabecalho[3])
        f = open(diretorioEntrada + nomeEntrada, 'wb+')
        recebidos = 0
        while recebidos < tamanho:
            r = con.recv(buff)
            while (r):
                recebidos += len(r)
                f.write(r)
                r = con.recv(buff)
            if not r:
                break

        print('\nFECHANDO ARQUIVO: ', diretorioEntrada + nomeEntrada, ' - RECEBIDOS: ', recebidos, ' de ', tamanho)
        f.close()
    elif comando == 'saida':   # Formato: saida|diretorio_job|nome_saida|tamanho|
        nomeDiretorio = cabecalho[1]
        diretorioSaida = './jobs/' + nomeDiretorio + '/saida/'
        nomeSaida = cabecalho[2]
        tamanho = int(cabecalho[3])
        f = open(diretorioSaida + nomeSaida, 'wb+')
        recebidos = 0
        while recebidos < tamanho:
            r = con.recv(buff)
            while (r):
                recebidos += len(r)
                f.write(r)
                r = con.recv(buff)
            if not r:
                break

        print('\nFECHANDO ARQUIVO ', diretorioSaida + nomeSaida, ' - RECEBIDOS: ', recebidos, ' de ', tamanho)
        f.close()

        # esta parte eh muito importante, nela mudamos o estado de uma tarefa concorrentemente
        if job.diretorio == nomeDiretorio:
            job.finalizaParte(nomeSaida, par)
    elif comando == 'executa':  # Formato da msg: executa|programa|diretorio_job|nome_entrada|remetente
        programa = cabecalho[1]
        nomeDiretorioJob = cabecalho[2]
        diretorioEntrada = './temp/' + nomeDiretorioJob + '/entrada/'
        diretorioSaida = './temp/' + nomeDiretorioJob + '/saida/'
        nomeEntrada = cabecalho[3]
        nomeSaida = nomeEntrada[0:-3] + '.out'
        remetente = par[0]
        resposta = ''
        try:
            print(f'\nIniciando execucao do programa {programa}')
            call(['./programs/' + programa, diretorioEntrada + nomeEntrada, diretorioSaida + nomeSaida])
            resposta = 'pronto'
        except Exception as e:
            print(f'\nERRO na execucao do programa {programa}')
            print(e)
            resposta = 'erro'
        enviaSaida(nomeDiretorioJob, nomeSaida, par)
    else:
        while (r):
            r = con.recv(buff)

    con.close()
#----------------------------------------------------------------------------------------

#-Thread do socket de boas-vindas do tcp-------------------------------------------------
def tcpThread():
    s = socket(AF_INET, SOCK_STREAM)
    s.bind(('', PORTA_TCP))
    s.listen(10)
    while True:
        con, par = s.accept()
        threading.Thread(target=conexaoTcpThread, args=tuple([con, par])).start()
#----------------------------------------------------------------------------------------

#-Inicializacao das threads--------------------------------------------------------------
try:
    threading.Thread(target=tcpThread, args=()).start()
    threading.Thread(target=recepcaoThread, args=()).start()
except Exception as e:
    print('Problemas com uma thread.')
    print(e)
    meuSocket.close()
    sys.exit(1)

print('Pronto.')
print('')
#----------------------------------------------------------------------------------------

#-Loop principal, usado para entrada de comandos-----------------------------------------
while True:
    try:
        comando = input('Comando: ')
        trataComando(comando)
    except KeyboardInterrupt:
        encerrarPrograma()
    except Exception as e:
        print('\nHouve um erro!')
        print(e)
#----------------------------------------------------------------------------------------
