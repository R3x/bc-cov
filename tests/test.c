#include <stdio.h> 

int main() {
    char c;
    int i;

    scanf("%c", &c);
    scanf("%d", &i);

    if (c == 'A') {
        if (i >= 90) {
            printf("Excellent\n");
        } else if (i >= 80) {
            printf("Good\n");
        } else {
            printf("Poor\n");
        }
    } else {
        if (i >= 80) {
            printf("Excellent\n");
        } else if (i >= 70) {
            printf("Good\n");
        } else {
            printf("Poor\n");
        }
    }
}