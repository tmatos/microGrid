import os
import datetime
import thread

lock = thread.allocate_lock() # Objeto para lock

# estados possiveis de uma parte
BRANCO = 'BRANCO'
ATRIBUIDO = 'ATRIBUIDO'
COMPLETO = 'COMPLETO'

class Parte:
    estado = BRANCO
    par = None
    data = None  # data de atribuicao
    entrada = None
    saida = None
    
    def is_branco(self):
        if self.estado == BRANCO:
            return True
        else:
            return False
    
    def is_atribuido(self):
        if self.estado == ATRIBUIDO:
            return True
        else:
            return False
    
    def is_completo(self):
        if self.estado == COMPLETO:
            return True
        else:
            return False
    
    def atribui(self, par):
        self.estado = ATRIBUIDO
        self.par = par
        self.data = datetime.datetime.now()
    
    def set_completo(self, saida):
        self.estado = COMPLETO
        self.saida = saida
        self.par = None
        self.data = None

class Job:
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
        
        dirEntrada = './jobs/' + diretorio + '/entrada'
        dirSaida = './jobs/' + diretorio + '/saida'
        
        print ''
        
        for file in os.listdir(dirEntrada):
            if file.endswith(".in"):
                parte = Parte()
                parte.entrada = file
                
                if os.path.isfile(dirSaida + '/' + file[0:-3] + '.out'):
                    parte.estado = COMPLETO
                    parte.saida = file[0:-3] + '.out'
                
                self.listaPartes.append(parte)
                self.partes = self.partes + 1
                print file, ' - ', parte.estado
        
        print 'Job carregado com ', self.partes, ' partes.'
    
    # True se todas tarefas estao completas, False se contrario
    def finalizado(self):
        valor = True
        
        lock.acquire()   ### Inicio de secao critica ###
        for p in self.listaPartes:
            if p.estado != COMPLETO:
                valor = False
                break
        lock.release()   ### Fim de secao critica ###
                
        return valor
    
    def inserePar(self, par):
        if par not in self.listaPares:
            self.listaPares.append(par)
    
    def removePar(self, par):
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
    
    # Atribui uma parte do job ao par especificado
    def atribuiParteAoPar(self, parte, par):
        ok = True
    
        lock.acquire()   ### Inicio de secao critica ###
        
        if parte not in self.listaPartes:
            print 'ERRO: Parte ', parte.entrada, ' nao esta no job ', self.nome
            ok = False
        elif par not in self.listaPares:
            print 'ERRO: Par ', par, ' nao participa no job ', self.nome
            ok = False
        elif parte.estado == COMPLETO:
            print 'NAO pode atribuir a parte ', parte.entrada, ' do job ', self.nome, ' pois ja esta completa.'
            ok = False
        elif par in self.listaParOcupado:
            print 'ERRO: Par ', par, ' ja esta ocupado com uma tarefa'
            ok = False
        elif parte.estado == ATRIBUIDO:
            print 'A PARTE ', parte.entrada, ' ja esta com ', parte.par
            ok = False
        
        # tudo ok, pode encadear
        if ok:
            self.listaPartes[self.listaPartes.index(parte)].atribui(par)
            self.listaParOcupado.append(par)
        
        lock.release()   ### Fim de secao critica ###
        
    def possuiParLivre(self):
        lock.acquire()   ### Inicio de secao critica ###
        if len(self.listaParOcupado) < len(self.listaPares):
            retorno = True
        else:
            retorno = False
        lock.release()   ### Fim de secao critica ###
            
        return retorno
        
    def proximoParLivre(self):
        parRetorno = None
    
        lock.acquire()   ### Inicio de secao critica ###
        for par in self.listaPares:
            if par not in self.listaParOcupado:
                parRetorno = par
        lock.release()   ### Fim de secao critica ###
        
        return parRetorno
        
    # Muda para COMPLETO o estado da parte que esta relacionada a nomeSaida
    # e tambem retira da listaParOcupado aquele que estiver com essa parte (se existir)
    def finalizaParte(self, nomeSaida, par):
        lock.acquire()   ### Inicio de secao critica ###
        
        for parte in self.listaPartes:
            if parte.entrada[0:-3] == nomeSaida[0:-4]: # correspondencia entre os nomes sem as extensoes
                # se a parte ja estiver completa, apenas passamos
                
                if parte.is_branco():
                    parte.set_completo(nomeSaida)
                elif parte.is_atribuido():
                    for parOcup in self.listaParOcupado:
                        print ' ' , parOcup[0]
                        if parOcup[0] == par[0]:
                            self.listaParOcupado.remove(parOcup)
                    parte.set_completo(nomeSaida)
                    
        lock.release()   ### Fim de secao critica ###
    
    # Retorna True se um dado par esta ocupado em alguma parte do job
    def isParOcupado(self, par):
        valor = False
        
        lock.acquire()   ### Inicio de secao critica ###
        for parOcup in self.listaParOcupado:
            if parOcup[0] == par[0]:
                valor = True
                break
        lock.release()   ### Fim de secao critica ###
        
        return valor