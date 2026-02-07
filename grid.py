# microGrid - Sistema de computacao em grid
# Copyright (C) 2026 Tiago Matos
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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

job = None  # pylint: disable=invalid-name

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
def processa_pacote_ok(msg : list, endereco_par : int) -> str:
    """
    Processa um pacote UDP do tipo 'ok' recebido de um par.
    """
    resposta = 'void'
    if msg[1] == 'contact':
        if len(lista_pares) < MAX_DE_PARES and endereco_par not in lista_pares:
            lista_pares.append(endereco_par)
            print(f'\nNosso pedido de contato foi aceito por {str(endereco_par)}')
        else:
            resposta = 'disconect'
    return resposta
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def processa_pacote_conect(endereco_par : int) -> str:
    """
    Processa um pacote UDP do tipo 'conect' recebido de um par.
    """
    resposta = 'void'
    if len(lista_pares) < MAX_DE_PARES:
        if endereco_par not in lista_pares:
            lista_pares.append(endereco_par)
        resposta = 'ok;contact'
        print(f'\nPedido de contato aceito originado de {str(endereco_par)}')
    else:
        resposta = 'not'
    return resposta
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def processa_pacote_disconect(endereco_par : int):
    """
    Processa um pacote UDP do tipo 'disconect' recebido de um par.
    """
    if endereco_par in lista_pares:
        lista_pares.remove(endereco_par)
        print(f'Contato desfeito por solicitacao de {str(endereco_par)}')
    else:
        print(f'Recebi disconect de {str(endereco_par)}, ele nao constava conectado.')
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def processa_pacote(msg_com_dados, endereco_par):
    """
    Processa um pacote UDP recebido de um par.
    """
    msg = msg_com_dados.decode('utf-8').split(';')  # Decode bytes to string
    resposta = 'void'
    if msg[0] == 'ok':
        resposta = processa_pacote_ok(msg, endereco_par)
    elif msg[0] == 'conect':
        resposta = processa_pacote_conect(endereco_par)
    elif msg[0] == 'disconect':
        processa_pacote_disconect(endereco_par)
    elif endereco_par in lista_pares:
        if msg[0] == 'do':
            resposta = 'what?'
            if len(msg) > 3:
                if msg[1] == 'cmd':
                    try:
                        call([f"./programs/{msg[2]}", msg[3]])
                        resposta = 'done cmd'
                    except Exception:  # Changed to catch all exceptions
                        resposta = 'erro cmd'
        elif msg[0] == 'msg':
            msg_print = f"Msg. de {str(endereco_par)} : "
            if len(msg) > 1:
                msg_print += msg[1]
            print('')
            print(msg_print)
            resposta = 'done'
    else:
        resposta = 'not'

    if resposta != 'void':
        meu_socket_udp.sendto(resposta.encode('utf-8'), endereco_par) # Encode string to bytes
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
    linhas_arquivo_pares = []

    try:
        with open('peerlist', encoding='utf-8') as file:
            linhas_arquivo_pares = [line.strip() for line in file]
    except OSError as ex:
        print('Erro ao acessar o arquivo peerlist!')
        print(ex)
        return

    if len(linhas_arquivo_pares) == 0:
        print('Arquivo peerlist vazio!')
    elif len(lista_pares) < len(linhas_arquivo_pares) and len(lista_pares) < 3:
        for endereco_par in linhas_arquivo_pares:
            meu_socket_udp.sendto(b'conect', (endereco_par, PORTA_UDP_PAR))  # Send bytes
            print(f'\nTentando contactar a: {endereco_par}')
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def enviar_arquivo(par, arquivo):
    """
    Transfere via TCP um arquivo para um par.
    """
    tcp_socket = socket(AF_INET, SOCK_STREAM)
    tcp_socket.connect((par[0], PORTA_TCP_PAR))
    with open(arquivo, 'rb', encoding='utf-8') as file:
        buff = 1024
        arquivo = arquivo.replace('\\', '/')
        nome = arquivo.split('/')[-1]
        tamanho = os.path.getsize(arquivo)
        cabecalho = f"envio|{nome}|{str(tamanho)}|"

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
    print('FIM DO ENVIO DE: ', arquivo)
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def prepara_job_no_par(par):
    """
    Prepara um par para receber o job carregado.
    """
    tcp_socket = socket(AF_INET, SOCK_STREAM)
    tcp_socket.connect((par[0], PORTA_TCP_PAR))
    tcp_socket.sendall(f"job|{job.diretorio}|".encode('utf-8'))
    buff = 1024
    print('')
    resp = tcp_socket.recv(buff).decode('utf-8')
    if resp == 'ok':
        print(f"PAR {par[0]} esta preparado para o job {job.nome}")
        job.insere_par(par)
    else:
        print(f"PAR {par[0]} nao pode preparar (ou nao e possivel confirmar este fato) ",
              f"para o job {job.nome}.")
        job.remove_par(par)
    tcp_socket.close()
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def envia_entrada(entrada : str, par):
    """
    Transfere via TCP um arquivo de entrada para um par.
    """
    file_path = f"./jobs/{job.diretorio}/entrada/{entrada}"

    try:
        with open(file_path, 'rb', encoding='utf-8') as file:
            tamanho = os.path.getsize(file_path)
            buff = 1024
            tcp_socket = socket(AF_INET, SOCK_STREAM)

            #formato: entrada|diretorio_job|nome_entrada|tamanho|
            cabecalho = f"entrada|{job.diretorio}|{entrada}|{str(tamanho)}|"

            # aqui preenchemos o cabecalho com esp. em branco ate ele ficar com tam. do buffer
            # isto e, o cabecalho deve ter buff bytes de tamanho (wrkrnd)
            cabecalho += ' ' * (1024 - len(cabecalho))

            try:
                print('ENVIANDO ENTRADA: ', file_path, ' de ', tamanho)
                tcp_socket.connect((par[0], PORTA_TCP_PAR))
                tcp_socket.send(cabecalho)
                dados = file.read(buff)
                while dados:
                    tcp_socket.send(dados)
                    dados = file.read(buff)
            except Exception as ex:
                print('\nHouve um erro na tranf. de um arquivo!')
                print(ex)
                return False
            finally:
                tcp_socket.close()
    except OSError as ex:
        print('ERRO ao acessar o arquivo de entrada ', file_path)
        print(ex)
        return False

    print('FIM DO ENVIO DE: ', file_path)
    return True
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def executa_parte_no_par(parte, par):
    """
    Envia um comando para o par executar uma parte do job.
    """
    tcp_socket = socket(AF_INET, SOCK_STREAM)

    # Formato: executa|programa|diretorio_job|nome_entrada|
    msg = f"executa|{job.programa}|{job.diretorio}|{parte.entrada}|"

    print('EXECUTANDO: ', job.programa, ' sobre a entrada ', parte.entrada, ' em ', par)

    tcp_socket.connect((par[0], PORTA_TCP_PAR))
    tcp_socket.send(msg)
    tcp_socket.close()
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def job_thread():
    """
    Thread que cuida da divisao e execucao das partes do job nos pares.
    """

    if len(lista_pares) == 0:
        print('\nSem contato de pares para compartilhar o processamento.')
        return

    # esse loop tambem popula a lista job.lista_pares com os pares prontos
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
    if not job:
        print('\nNenhum job carregado.')
        return
    if len(job.lista_partes) == 0:
        print('\nJob sem tarefas.')
        return
    if job.finalizado():
        print(f"\nTodas as tarefas do job \'{job.nome}\' foram completas.")
        return

    for parte in job.lista_partes:
        if parte.is_branco():
            print('PARTE: ', parte.entrada, ' EM BRANCO')

    threading.Thread(target=job_thread, args=()).start()
#----------------------------------------------------------------------------------------

#-Carrega para a memoria o job descrito pelo arquivo-------------------------------------
def carrega_job(nome_arquivo : str):
    """
    Carrega um job a partir de um arquivo .job especificado.
    """
    global job  # pylint: disable=global-statement,invalid-name
    arquivo_job = []

    try:
        with open(f"jobs/{nome_arquivo}", encoding='utf-8') as file:
            if not file:
                print(f'Arquivo de job {nome_arquivo} nao encontrado.')
                return
            for line in file:
                entrada = line.strip()
                if len(entrada) > 0 and entrada[0] != '#':
                    arquivo_job.append(entrada)
    except OSError as ex:
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

def executa_comando_mensagem(comando : list):
    """
    Executa o comando de envio de mensagem para um par.
    """
    if len(comando) < 3:
        print('\nArgumentos incorretos no comando.')
        return
    try:
        id_par = int(comando[1])
        if id_par < 0:
            raise ValueError
    except ValueError:
        print('\nArgumentos incorretos no comando. ',
              'O id do par deve ser numero inteiro nao negativo.')
        return
    envia_mensagem(id_par, comando[2:])
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def executa_comando_enviar(comando : list):
    """
    Executa o comando de envio arquivo para um par.
    """
    if len(comando) < 3:
        print('\nArgumentos incorretos no comando.')
        return
    try:
        id_par = int(comando[1])
        if id_par < 0:
            raise ValueError
    except ValueError:
        print('\nArgumentos incorretos no comando. ',
              'O id do par deve ser numero inteiro nao negativo.')
        return
    if id_par+1 > len(lista_pares):
        print('\nNao temos este par na nossa lista.')
        return
    enviar_arquivo(lista_pares[id_par], comando[2])
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def executa_comando_pares():
    """
    Executa o comando de listar pares contactados.
    """
    i = 0
    for par in lista_pares:
        print('#', i, ' - ', str(par),
              ' - Ocup.:', job.is_par_ocupado(par) if job is not None else False)
        i = i + 1
    if i == 0:
        print('Sem pares contactados.')
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def executa_comando_carrega(comando : list):
    """
    Executa o comando de carregar um job.
    """
    if len(comando) < 2:
        print('\nArgumentos incorretos. Especifique o arquivo do job.')
        return
    carrega_job(comando[1])
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def executa_comando_estado():
    """
    Executa o comando de exibir o estado do job.
    """
    if job is None:
        print('Sem job carregado.')
    else:
        job.print_status()
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def trata_comando(string_comando : str):
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
        executa_comando_mensagem(comando)
    elif comando[0] == 'enviar':
        executa_comando_enviar(comando)
    elif comando[0] == 'pares':
        executa_comando_pares()
    elif comando[0] == 'carrega':
        executa_comando_carrega(comando)
    elif comando[0] == 'estado':
        executa_comando_estado()
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
def envia_saida(diretorio : str, saida : str, par):
    """
    Transfere via TCP resultados sobre o processamento e o arquivo de saida (caso haja)
    gerado por um job para um determinado par.
    """
    file_path = f"./temp/{diretorio}/saida/{saida}"

    try:
        with open(file_path, 'rb', encoding='utf-8') as file:
            tamanho = os.path.getsize(file_path)
            buff = 1024
            tcp_socket = socket(AF_INET, SOCK_STREAM)

            # formato: saida|diretorio_job|nome_saida|tamanho|
            cabecalho = f"saida|{diretorio}|{saida}|{str(tamanho)}|"

            # aqui preenchemos o cabecalho com esp. em branco ate ele ficar com tam. do buffer
            # isto e, o cabecalho deve ter buff bytes de tamanho (wrkrnd)
            cabecalho += ' ' * (1024 - len(cabecalho))

            print(f"\nENVIANDO SAIDA: {file_path} de {str(tamanho)} bytes")

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
                return False
            tcp_socket.close()
    except OSError as ex_os_error:
        print(f'\nERRO ao acessar o arquivo de saida {file_path}')
        print(ex_os_error)
        return False

    print(f'\nFIM DO ENVIO DE: {file_path}')
    return True
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def trata_comando_tcp_envio(con, nome : str, tamanho : int):
    """
    Trata a recepcao de arquivo via TCP oriundo de um outro par.
    """
    buff = 1024
    with open(f'./recebidos/{nome}', 'wb+', encoding='utf-8') as file:
        recebidos = 0
        while recebidos < tamanho:
            resp = con.recv(buff)
            while resp:
                recebidos += len(resp)
                file.write(resp)
                resp = con.recv(buff)
            if not resp:
                break
        print('\nFECHANDO ARQUVIO', '- RECEBIDOS: ', recebidos, ' bytes,')
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def trata_comando_tcp_job(con, diretorio_job : str):
    """
    Recebe o comando de algum um par para ficar preparado a receber um novo job.
    """
    resultado = ''
    try:
        if not os.path.isdir(diretorio_job):
            os.makedirs(diretorio_job + '/entrada')
            os.makedirs(diretorio_job + '/saida')
        resultado = 'ok'
    except Exception as ex:
        resultado = 'erro'
        print(ex)
    con.send(resultado)
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def trata_comando_tcp_entrada(con, dir_entrada, nome_entrada, tamanho):
    """
    Trata a recepcao de arquivo de entrada via TCP oriundo de um outro par.
    """
    buff = 1024
    file_path = dir_entrada + nome_entrada
    with open(file_path, 'wb+', encoding='utf-8') as file:
        recebidos = 0
        while recebidos < tamanho:
            resp = con.recv(buff)
            while resp:
                recebidos += len(resp)
                file.write(resp)
                resp = con.recv(buff)
            if not resp:
                break
        print('\nFECHANDO ARQUIVO: ', file_path,
              ' - RECEBIDOS: ', recebidos, ' de ', tamanho)
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def trata_comando_tcp_saida(con, par, nome_dir : str, nome_saida : str, tamanho : int):
    """
    Trata a recepcao de arquivo de saida via TCP oriundo de um outro par.
    """
    buff = 1024
    diretorio_saida = f"./jobs/{nome_dir}/saida/"
    file_path = diretorio_saida + nome_saida
    with open(file_path, 'wb+', encoding='utf-8') as file:
        recebidos = 0
        while recebidos < tamanho:
            resp = con.recv(buff)
            while resp:
                recebidos += len(resp)
                file.write(resp)
                resp = con.recv(buff)
            if not resp:
                break
        print('\nFECHANDO ARQUIVO: ', file_path,
              ' - RECEBIDOS: ', recebidos, ' de ', tamanho)
    # esta parte eh muito importante, nela mudamos o estado duma tarefa concorrentemente
    if job.diretorio == nome_dir:
        job.finaliza_parte(nome_saida, par)
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def trata_comando_tcp_executa(par, programa, dir_job, nome_entrada, nome_saida):
    """
    Trata o comando de execucao de um programa sobre um arquivo de entrada,
    e ja faz envio de resultado e arquivo de saida ao par que solicitou a execucao.
    """
    dir_entrada = f'./temp/{dir_job}/entrada/'
    dir_saida = f'./temp/{dir_job}/saida/'
    try:
        print(f'\nIniciando execucao do programa {programa}')
        call([f'./programs/{programa}',
                dir_entrada + nome_entrada,
                dir_saida + nome_saida])
        #resposta = 'pronto'
    except Exception as ex:
        print(f'\nERRO na execucao do programa {programa}')
        print(ex)
        #resposta = 'erro'
    envia_saida(dir_job, nome_saida, par)
    # NOTE: avaliar a possibilidade de enviar a conexao 'con' por aqui,
    #       evitando a necessidade de abrir nova conexao TCP dentro da func acima
#----------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------
def conexao_tcp_thread(con, par):
    """
    Thread que cuida de uma conexao TCP criada pela interacao com um par.
    """
    buff = 1024
    resp = con.recv(buff).decode('utf-8')

    cabecalho = resp.split('|')
    comando = cabecalho[0]

    if comando == 'envio':
        nome = cabecalho[1]
        tamanho = int(cabecalho[2])
        trata_comando_tcp_envio(con, nome, tamanho)

    elif comando == 'job':
        diretorio_job = f"./temp/{cabecalho[1]}"
        trata_comando_tcp_job(con, diretorio_job)

    elif comando == 'entrada':
        # Formato: entrada|diretorio|nome_entrada|tamanho|
        dir_entrada = f"./temp/{cabecalho[1]}/entrada/"
        nome_entrada = cabecalho[2]
        tamanho = int(cabecalho[3])
        trata_comando_tcp_entrada(con, dir_entrada, nome_entrada, tamanho)

    elif comando == 'saida':
        # Formato: saida|diretorio_job|nome_saida|tamanho|
        nome_diretorio = cabecalho[1]
        nome_saida = cabecalho[2]
        tamanho = int(cabecalho[3])
        trata_comando_tcp_saida(con, par, nome_diretorio, nome_saida, tamanho)

    elif comando == 'executa':
        # Formato da msg: executa|programa|diretorio_job|nome_entrada|remetente
        programa = cabecalho[1]
        dir_job = cabecalho[2]
        nome_entrada = cabecalho[3]
        nome_saida = nome_entrada[0:-3] + '.out'
        trata_comando_tcp_executa(par, programa, dir_job, nome_entrada, nome_saida)

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
