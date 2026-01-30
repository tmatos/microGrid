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
    listaPartes = []
    listaPares = []
    listaParOcupado = []

    def __init__(self, nome, programa, diretorio, arquivo):
        self.nome = nome
        self.programa = programa
        self.diretorio = diretorio
        self.arquivo = arquivo
        dirEntrada = f'./jobs/{diretorio}/entrada'
        dirSaida = f'./jobs/{diretorio}/saida'
        print('')

        for file in os.listdir(dirEntrada):
            if file.endswith(".in"):
                parte = Parte()
                parte.entrada = file
                if os.path.isfile(f'{dirSaida}/{file[:-3]}.out'):
                    parte.estado = COMPLETO
                    parte.saida = f'{file[:-3]}.out'
                self.listaPartes.append(parte)
                self.partes += 1
                print(file, ' - ', parte.estado)

        print('Job carregado com ', self.partes, ' partes.')

    def finalizado(self):
        """
        Retorna True se todas as partes do job estiverem completas.
        """
        valor = True
        lock.acquire()   ### Inicio de secao critica ###
        for p in self.listaPartes:
            if p.estado != COMPLETO:
                valor = False
                break
        lock.release()   ### Fim de secao critica ###
        return valor

    def inserePar(self, par):
        """
        Insere um par na lista de pares que participam do job.
        """
        if par not in self.listaPares:
            self.listaPares.append(par)

    def removePar(self, par):
        """
        Remove um par da lista de pares que participam do job.
        """
        if par in self.listaPares:
            self.listaPares.remove(par)
            if par in self.listaParOcupado:
                self.listaParOcupado.remove(par)
                for t in self.listaPartes:
                    if t.estado == ATRIBUIDO:
                        if t.par == par:
                            t.estado = BRANCO
                            t.par = None
                            t.data = None

    def atribuiParteAoPar(self, parte, par):
        """
        Atribui uma parte do job ao par especificado        
        """
        ok = True
        lock.acquire()   ### Inicio de secao critica ###
        if parte not in self.listaPartes:
            print('ERRO: Parte ', parte.entrada, ' nao esta no job ', self.nome)
            ok = False
        elif par not in self.listaPares:
            print('ERRO: Par ', par, ' nao participa no job ', self.nome)
            ok = False
        elif parte.estado == COMPLETO:
            print('NAO pode atribuir a parte ', parte.entrada, ' do job ', self.nome, ' pois ja esta completa.')
            ok = False
        elif par in self.listaParOcupado:
            print('ERRO: Par ', par, ' ja esta ocupado com uma tarefa')
            ok = False
        elif parte.estado == ATRIBUIDO:
            print('A PARTE ', parte.entrada, ' ja esta com ', parte.par)
            ok = False
        # tudo ok, pode encadear
        if ok:
            self.listaPartes[self.listaPartes.index(parte)].atribui(par)
            self.listaParOcupado.append(par)
        lock.release()   ### Fim de secao critica ###

    def possuiParLivre(self):
        """
        Retorna True se houver algum par livre para receber uma parte.
        """
        lock.acquire()   ### Inicio de secao critica ###
        retorno = len(self.listaParOcupado) < len(self.listaPares)
        lock.release()   ### Fim de secao critica ###
        return retorno

    def proximoParLivre(self):
        """
        Retorna o proximo par livre para receber uma parte.
        """
        parRetorno = None
        lock.acquire()   ### Inicio de secao critica ###
        for par in self.listaPares:
            if par not in self.listaParOcupado:
                parRetorno = par
                break
        lock.release()   ### Fim de secao critica ###
        return parRetorno

    def finalizaParte(self, nomeSaida, par):        
        """
        Muda para COMPLETO o estado da parte que esta relacionada a nomeSaida
        e também retira da listaParOcupado aquele que estiver com essa parte (se existir).
        """
        lock.acquire()   ### Inicio de secao critica ###
        for parte in self.listaPartes:
            if parte.entrada[:-3] == nomeSaida[:-4]:  # correspondencia entre os nomes sem as extensoes
                # se a parte ja estiver completa, apenas passamos
                if parte.is_branco():
                    parte.set_completo(nomeSaida)
                elif parte.is_atribuido():
                    for parOcup in self.listaParOcupado:
                        if parOcup[0] == par[0]:
                            self.listaParOcupado.remove(parOcup)
                    parte.set_completo(nomeSaida)
        lock.release()   ### Fim de secao critica ###

    def isParOcupado(self, par):
        """
        Retorna True se um dado par está ocupado em alguma parte do job.
        """
        valor = False
        lock.acquire()   ### Inicio de secao critica ###
        for parOcup in self.listaParOcupado:
            if parOcup[0] == par[0]:
                valor = True
                break
        lock.release()   ### Fim de secao critica ###
        return valor
