// Enumerate every subset XOR of the page's token digests via Gray code.
// XOR is commutative and self-inverse, so subsets - not permutations - are the
// real space, and the Dualite key is one point in it.
#include <stdio.h>
#include <string.h>
#include <openssl/sha.h>
static const char *T[]={
"matrixsumlist","enter","lastwordsbeforearchichoice","thispassword",
"yourlastcommand","secondanswer","ourfirsthintisyourlastcommand","shabef",
"sha256","anstoo","shabefanstoo","btcseed","theseedisplanted","causality",
"salphaseion","cosmicduality","dualite","esrever","archichoice","firsthint",
"lastcommand","half","betterhalf","whiterabbit"};
#define NT 24
int main(void){
    unsigned char d[NT][32], acc[32]={0};
    for(int i=0;i<NT;i++) SHA256((const unsigned char*)T[i],strlen(T[i]),d[i]);
    static const char*H="0123456789abcdef";
    char out[66]; out[64]='\n'; out[65]=0;
    unsigned long total=1UL<<NT;
    for(unsigned long g=1; g<total; g++){
        unsigned long gray=g^(g>>1), prev=(g-1)^((g-1)>>1), diff=gray^prev;
        int bit=__builtin_ctzl(diff);
        for(int j=0;j<32;j++) acc[j]^=d[bit][j];
        for(int j=0;j<32;j++){ out[2*j]=H[acc[j]>>4]; out[2*j+1]=H[acc[j]&15]; }
        fwrite(out,1,65,stdout);
    }
    return 0;
}
