#include<stdio.h>

int main(int argc, char* argv[])
{
	if(argc < 3) exit(0);
	
	FILE *arquivo = fopen(argv[1], "r");
	
    if(!arquivo)
	{
		printf("\nINVERSA\nErro com arquivo de entrada.\n");
		return 1;
    }
	
	FILE *saida = fopen(argv[2], "w");
	
	if(!saida)
	{
		printf("\nINVERSA\nErro com gravacao de arquivo de saida.\n");
		return 1;
    }
	
    float matrix[100][100], ratio, a;
    int i, j, k, n;
    
    fscanf(arquivo, "%d\n", &n);
    
    for(i = 0; i < n; i++) {
        for(j = 0; j < n; j++) {
            fscanf(arquivo, "%f\n", &matrix[i][j]);
        }
    }
    
    for(i = 0; i < n; i++) {
        for(j = n; j < 2*n; j++) {
            if(i==(j-n))
                matrix[i][j] = 1.0;
            else
                matrix[i][j] = 0.0;
        }
    }
    
    for(i = 0; i < n; i++) {
        for(j = 0; j < n; j++) {
            if(i!=j){
                ratio = matrix[j][i]/matrix[i][i];
                for(k = 0; k < 2*n; k++){
                    matrix[j][k] -= ratio * matrix[i][k];
                }
            }
        }
    }
    
    for(i = 0; i < n; i++) {
        a = matrix[i][i];
        for(j = 0; j < 2*n; j++) {
            matrix[i][j] /= a;
        }
    }
    
    for(i = 0; i < n; i++) {
        for(j = n; j < 2*n; j++) {
            fprintf(saida, "%.2f", matrix[i][j]);
            fprintf(saida, "\t");
        }
        fprintf(saida, "\n");
    }
    
    return 0;
}
