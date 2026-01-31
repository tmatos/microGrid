"""
Modulo que implementa a classe Job e Parte para o sistema de distribuicao de tarefas.
"""

import os
import datetime
import threading

lock = threading.Lock()

# estados possiveis de uma parte
BRANCO = 'BRANCO'
ATRIBUIDO = 'ATRIBUIDO'
COMPLETO = 'COMPLETO'

class Parte:
    """
    Representa uma parte de um job.
    """
    estado = BRANCO
    par = None
    data = None  # data de atribuicao
    entrada = None
    saida = None

    def is_branco(self):
        """
        Retorna True se a parte esta em estado BRANCO.
        """
        return self.estado == BRANCO

    def is_atribuido(self):
        """
        Retorna True se a parte esta em estado ATRIBUIDO.
        """
        return self.estado == ATRIBUIDO

    def is_completo(self):
        """
        Retorna True se a parte esta em estado COMPLETO.
        """
        return self.estado == COMPLETO

    def atribui(self, par):
        """
        Atribui a parte ao par especificado.
        """
        self.estado = ATRIBUIDO
        self.par = par
        self.data = datetime.datetime.now()

    def set_completo(self, saida):
        """
        Marca a parte como COMPLETO, definindo o nome do arquivo de saida.
        """
        self.estado = COMPLETO
        self.saida = saida
        self.par = None
        self.data = None

class Job:
    """
    Representa um job para processamento, composto por varias partes.
    """
    nome = None
    programa = None
    diretorio = None
    arquivo = None
    partes = 0
    lista_partes = []
    lista_pares = []
    lista_par_ocupado = []

    def __init__(self, nome, programa, diretorio, arquivo):
        self.nome = nome
        self.programa = programa
        self.diretorio = diretorio
        self.arquivo = arquivo
        dir_entrada = f'./jobs/{diretorio}/entrada'
        dir_saida = f'./jobs/{diretorio}/saida'
        print('')

        for file in os.listdir(dir_entrada):
            if file.endswith(".in"):
                parte = Parte()
                parte.entrada = file
                if os.path.isfile(f'{dir_saida}/{file[:-3]}.out'):
                    parte.estado = COMPLETO
                    parte.saida = f'{file[:-3]}.out'
                self.lista_partes.append(parte)
                self.partes += 1
                print(file, ' - ', parte.estado)

        print('Job carregado com ', self.partes, ' partes.')

    def finalizado(self):
        """
        Retorna True se todas as partes do job estiverem completas.
        """
        valor = True
        lock.acquire()   ### Inicio de secao critica ###
        for parte in self.lista_partes:
            if parte.estado != COMPLETO:
                valor = False
                break
        lock.release()   ### Fim de secao critica ###
        return valor

    def insere_par(self, par):
        """
        Insere um par na lista de pares que participam do job.
        """
        if par not in self.lista_pares:
            self.lista_pares.append(par)

    def remove_par(self, par):
        """
        Remove um par da lista de pares que participam do job.
        """
        if par in self.lista_pares:
            self.lista_pares.remove(par)
            if par in self.lista_par_ocupado:
                self.lista_par_ocupado.remove(par)
                for parte in self.lista_partes:
                    if parte.estado == ATRIBUIDO:
                        if parte.par == par:
                            parte.estado = BRANCO
                            parte.par = None
                            parte.data = None

    def atribui_parte_ao_par(self, parte, par):
        """
        Atribui uma parte do job ao par especificado
        """
        ok = True
        lock.acquire()   ### Inicio de secao critica ###
        if parte not in self.lista_partes:
            print('ERRO: Parte ', parte.entrada, ' nao esta no job ', self.nome)
            ok = False
        elif par not in self.lista_pares:
            print('ERRO: Par ', par, ' nao participa no job ', self.nome)
            ok = False
        elif parte.estado == COMPLETO:
            print('NAO pode atribuir a parte ', parte.entrada, ' do job ', self.nome, ' pois ja esta completa.')
            ok = False
        elif par in self.lista_par_ocupado:
            print('ERRO: Par ', par, ' ja esta ocupado com uma tarefa')
            ok = False
        elif parte.estado == ATRIBUIDO:
            print('A PARTE ', parte.entrada, ' ja esta com ', parte.par)
            ok = False
        # tudo ok, pode encadear
        if ok:
            self.lista_partes[self.lista_partes.index(parte)].atribui(par)
            self.lista_par_ocupado.append(par)
        lock.release()   ### Fim de secao critica ###

    def possui_par_livre(self):
        """
        Retorna True se houver algum par livre para receber uma parte.
        """
        lock.acquire()   ### Inicio de secao critica ###
        retorno = len(self.lista_par_ocupado) < len(self.lista_pares)
        lock.release()   ### Fim de secao critica ###
        return retorno

    def proximo_par_livre(self):
        """
        Retorna o proximo par livre para receber uma parte.
        """
        par_retorno = None
        lock.acquire()   ### Inicio de secao critica ###
        for par in self.lista_pares:
            if par not in self.lista_par_ocupado:
                par_retorno = par
                break
        lock.release()   ### Fim de secao critica ###
        return par_retorno

    def finaliza_parte(self, nome_saida, par):
        """
        Muda para COMPLETO o estado da parte que esta relacionada a nomeSaida
        e também retira da listaParOcupado aquele que estiver com essa parte (se existir).
        """
        lock.acquire()   ### Inicio de secao critica ###
        for parte in self.lista_partes:
            if parte.entrada[:-3] == nome_saida[:-4]:  # correspondencia entre os nomes sem as extensoes
                # se a parte ja estiver completa, apenas passamos
                if parte.is_branco():
                    parte.set_completo(nome_saida)
                elif parte.is_atribuido():
                    for par_ocupado in self.lista_par_ocupado:
                        if par_ocupado[0] == par[0]:
                            self.lista_par_ocupado.remove(par_ocupado)
                    parte.set_completo(nome_saida)
        lock.release()   ### Fim de secao critica ###

    def is_par_ocupado(self, par):
        """
        Retorna True se um dado par está ocupado em alguma parte do job.
        """
        valor = False
        lock.acquire()   ### Inicio de secao critica ###
        for par_ocupado in self.lista_par_ocupado:
            if par_ocupado[0] == par[0]:
                valor = True
                break
        lock.release()   ### Fim de secao critica ###
        return valor

    def print_status(self):
        """
        Imprime em stdout o estado do job.
        """
        lock.acquire()  ### Inicio de secao critica ###
        for parte in self.lista_partes:
            print('#', parte.entrada, '-', parte.estado)
        lock.release()  ### Fim de secao critica ###
