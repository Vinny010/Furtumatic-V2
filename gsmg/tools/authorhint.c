/* Author's 2023 hint token set: "yellow blue primes matrix sumlist
   lastwordsbeforearchichoice yinyang" - plus the grid counts (15 blue, 9 yellow),
   O=15 / I=9 from a1z26, and prime forms. Concatenations WITH repetition, len 1..5. */
#include <stdio.h>
#include <string.h>
static const char *T[]={
 "yellow","blue","primes","prime","matrix","sumlist","matrixsumlist",
 "lastwordsbeforearchichoice","yinyang","yin","yang",
 "15","9","159","915","o","i","oi","io",
 "23571113","2357111317","thematrixhasyou","enter","thispassword"};
#define NT 24
static char buf[4096];
static void rec(int d,int maxd,int len){
    if(d>0){buf[len]=0;puts(buf);}
    if(d==maxd) return;
    for(int i=0;i<NT;i++){
        int l=strlen(T[i]);
        if(len+l>=3500) continue;
        memcpy(buf+len,T[i],l);
        rec(d+1,maxd,len+l);
    }
}
int main(void){ rec(0,5,0); return 0; }
