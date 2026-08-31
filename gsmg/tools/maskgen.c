// 256-symbol object over 23 letters: assign each letter one bit -> 256 bits ->
// 32 bytes. Enumerate all 2^23 masks by Gray code, emit hex, forward+reverse.
#include <stdio.h>
#include <string.h>
static char obj[300]; static int n=0, nl=0;
static int li[300];              // letter index per symbol
static unsigned char bitv[23];
static const char*H="0123456789abcdef";
static void emit(int rev){
    unsigned char b[32]; memset(b,0,32);
    for(int i=0;i<256;i++){
        int s = rev ? li[255-i] : li[i];
        if(bitv[s]) b[i>>3] |= 0x80>>(i&7);
    }
    char out[66];
    for(int j=0;j<32;j++){ out[2*j]=H[b[j]>>4]; out[2*j+1]=H[b[j]&15]; }
    out[64]='\n'; fwrite(out,1,65,stdout);
}
int main(void){
    FILE*f=fopen("object256_real.txt","r");
    if(!fgets(obj,sizeof obj,f)) return 1; fclose(f);
    n=strlen(obj); while(n&&(obj[n-1]=='\n'||obj[n-1]=='\r')) obj[--n]=0;
    char seen[256]; memset(seen,-1,sizeof seen);
    for(int i=0;i<n;i++){
        unsigned char c=obj[i];
        if(seen[c]<0){ seen[c]=nl++; }
        li[i]=seen[c];
    }
    fprintf(stderr,"object %d symbols, %d distinct letters -> 2^%d masks\n",n,nl,nl);
    if(n!=256) { fprintf(stderr,"expected 256 symbols\n"); return 1; }
    unsigned long total=1UL<<nl;
    for(unsigned long g=0; g<total; g++){
        unsigned long gray=g^(g>>1);
        for(int i=0;i<nl;i++) bitv[i]=(gray>>i)&1;
        emit(0); emit(1);
    }
    return 0;
}
