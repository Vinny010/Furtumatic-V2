/* Concatenations WITH REPETITION of the page's token set, lengths 2..5.
   Every prior sweep used permutations, which cannot repeat a token - yet the
   known password shape (issue #108) repeats matrixsumlist. This closes that hole. */
#include <stdio.h>
#include <string.h>
static const char *T[]={
 "matrixsumlist","enter","lastwordsbeforearchichoice","thispassword",
 "yourlastcommand","secondanswer","ourfirsthintisyourlastcommand",
 "causality","theseedisplanted","btcseed","esrever","salphaseion",
 "cosmicduality","half","betterhalf","sha256","shabef","anstoo",
 "thematrixhasyou","fubcd"};
#define NT 20
static char buf[4096];
static void rec(int depth,int maxd,int len){
    if(depth>0){ buf[len]=0; puts(buf); }
    if(depth==maxd) return;
    for(int i=0;i<NT;i++){
        int l=strlen(T[i]);
        if(len+l>=4000) continue;
        memcpy(buf+len,T[i],l);
        rec(depth+1,maxd,len+l);
    }
}
int main(void){ rec(0,5,0); return 0; }
