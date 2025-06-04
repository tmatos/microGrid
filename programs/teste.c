#include <stdio.h>
#include <stdlib.h>

int main(int argc, char* argv[])
{
	int i;
	
	if (argc > 1)
	{
		for (i = 0 ; i < argc ; i++)
		{
			printf("#%d = %s\n", i, argv[i]);
		}
		
		if (argc == 2)
		{
			printf("Testar um.\n");

			int a = atoi(argv[1]);
		}
		else if (argc == 3)
		{
			printf("Testar intervalo.\n");
			
			int a = atoi(argv[1]);
			int b = atoi(argv[2]);
		}
	}
	
	return 0;
}
