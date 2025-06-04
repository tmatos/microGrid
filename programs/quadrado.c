#include <stdio.h>
#include <stdlib.h>

int main(int argc, char* argv[])
{
    if (argc < 3)
    {
        printf("Uso: quadrado [arquivo de entrada] [arquivo de saida]\n\n");
        return 0;
    }
    
    FILE *arquivo = fopen(argv[1], "r");
    
    if (!arquivo)
    {
        printf("\nQUADRADO\nErro com arquivo de entrada.\n");
        return 1;
    }
    
    FILE *saida = fopen(argv[2], "w");
    
    if (!saida)
    {
        printf("\nQUADRADO\nErro com gravacao de arquivo de saida.\n");
        return 1;
    }
    
    int valor;
        
    while (!feof(arquivo))
    {
        fscanf(arquivo, "%d\n", &valor);
        fprintf(saida, "%d^2 = %d\n", valor, valor*valor);
    }
    
    fclose(arquivo);
    
    return 0;
}
