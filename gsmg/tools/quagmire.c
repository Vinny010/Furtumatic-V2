/* Quagmire-type solver: period-15 polyalphabetic over a permuted 26-symbol
   alphabet. Anneals the alphabet permutation AND the 15 key values jointly --
   the previous version re-solved keys by chi-squared at every step, which made
   the landscape discontinuous under a single swap. */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#define A 26
static int N,L=15,ct[4096];
static double TRI[26*26*26];
static int rho[A],key[64],pt[4096],MODE;
static double ENG[26]={8.167,1.492,2.782,4.253,12.702,2.228,2.015,6.094,6.966,0.153,
 0.772,4.025,2.406,6.749,7.507,1.929,0.095,5.987,6.327,9.056,2.758,0.978,2.360,0.150,1.974,0.074};
static int colcnt[64][A],collen[64];
static inline int dec(int s,int c){
    return MODE ? ((rho[s]-key[c])%A+A)%A : ((key[c]-rho[s])%A+A)%A;
}
static double score(void){
    for(int i=0;i<N;i++) pt[i]=dec(ct[i],i%L);
    double s=0;
    for(int i=0;i+2<N;i++) s+=TRI[pt[i]*676+pt[i+1]*26+pt[i+2]];
    return s;
}
static void chi_keys(void){
    for(int c=0;c<L;c++){
        double bs=1e30; int bk=0;
        for(int k=0;k<A;k++){
            int cnt[A]; memset(cnt,0,sizeof cnt);
            for(int s=0;s<A;s++) if(colcnt[c][s]){
                int p=MODE?((rho[s]-k)%A+A)%A:((k-rho[s])%A+A)%A;
                cnt[p]+=colcnt[c][s];
            }
            double sc=0,n=collen[c];
            for(int i=0;i<A;i++){double e=n*ENG[i]/100.0;sc+=(cnt[i]-e)*(cnt[i]-e)/e;}
            if(sc<bs){bs=sc;bk=k;}
        }
        key[c]=bk;
    }
}
int main(int argc,char**argv){
    long iters = argc>1?atol(argv[1]):3000000;
    int restarts = argc>2?atoi(argv[2]):60;
    FILE*f=fopen("tri.txt","r");
    for(int i=0;i<26*26*26;i++) if(fscanf(f,"%lf",&TRI[i])!=1) return 1;
    fclose(f);
    f=fopen("ct.txt","r"); N=0; while(fscanf(f,"%d",&ct[N])==1) N++; fclose(f);
    for(int i=0;i<N;i++){colcnt[i%L][ct[i]]++;collen[i%L]++;}
    srandom(20260831);
    double bestall=-1e30; int brho[A],bkey[64],bmode=0;
    for(int m=0;m<2;m++){
      MODE=m;
      for(int r=0;r<restarts;r++){
        for(int i=0;i<A;i++) rho[i]=i;
        for(int i=A-1;i>0;i--){int j=random()%(i+1),t=rho[i];rho[i]=rho[j];rho[j]=t;}
        chi_keys();
        double cur=score(),T=4.0;
        for(long it=0;it<iters;it++){
            int a=0,b=0,c=0,oldk=0,kind=(random()%3==0);
            if(kind){ c=random()%L; oldk=key[c]; key[c]=random()%A; }
            else { a=random()%A; b=random()%A; if(a==b) continue;
                   int t=rho[a];rho[a]=rho[b];rho[b]=t; }
            double s=score();
            if(s>cur || ((double)random()/RAND_MAX)<exp((s-cur)/T)) cur=s;
            else { if(kind) key[c]=oldk;
                   else {int t=rho[a];rho[a]=rho[b];rho[b]=t;} }
            T*=0.9999975; if(T<0.03)T=0.03;
        }
        double s=score();
        if(s>bestall){bestall=s;memcpy(brho,rho,sizeof rho);memcpy(bkey,key,sizeof key);bmode=m;
            fprintf(stderr,"mode=%d r=%d score=%.0f (%.3f/char) key=",m,r,s,s/N);
            for(int c2=0;c2<L;c2++) fputc('A'+key[c2],stderr);
            fprintf(stderr,"  ");
            for(int i=0;i<64;i++) fputc('A'+pt[i],stderr);
            fprintf(stderr,"\n"); fflush(stderr);
        }
      }
    }
    MODE=bmode; memcpy(rho,brho,sizeof rho); memcpy(key,bkey,sizeof key); score();
    printf("mode=%s score=%.0f (%.3f/char)\nkey=",bmode?"vigenere":"beaufort",bestall,bestall/N);
    for(int c=0;c<L;c++) putchar('A'+key[c]);
    printf("\n");
    for(int i=0;i<N;i++) putchar('A'+pt[i]);
    printf("\n");
    return 0;
}
