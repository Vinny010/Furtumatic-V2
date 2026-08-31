/* General polyalphabetic solver: 15 INDEPENDENT substitution alphabets.
   Subsumes every Quagmire variant. Within a column, plaintext is every 15th
   character of English, so trigram signal comes only from ACROSS columns --
   which is exactly what the objective measures. */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#define A 26
static int N,L=15,ct[4096];
static double TRI[26*26*26];
static int alpha[16][A], pt[4096];
static double score(void){
    for(int i=0;i<N;i++) pt[i]=alpha[i%L][ct[i]];
    double s=0;
    for(int i=0;i+2<N;i++) s+=TRI[pt[i]*676+pt[i+1]*26+pt[i+2]];
    return s;
}
int main(int argc,char**argv){
    long iters=argc>1?atol(argv[1]):8000000;
    int restarts=argc>2?atoi(argv[2]):12;
    FILE*f=fopen("tri.txt","r");
    for(int i=0;i<26*26*26;i++) if(fscanf(f,"%lf",&TRI[i])!=1) return 1;
    fclose(f);
    f=fopen("ct.txt","r"); N=0; while(fscanf(f,"%d",&ct[N])==1) N++; fclose(f);
    /* seed each column by frequency: most common symbol -> E, etc. */
    static const int ORD[26]={4,19,0,14,8,13,18,7,17,3,11,2,20,12,22,5,6,24,15,1,21,10,9,23,16,25};
    srandom(2718);
    double best=-1e30; static int balpha[16][A];
    for(int r=0;r<restarts;r++){
        for(int c=0;c<L;c++){
            int cnt[A]; memset(cnt,0,sizeof cnt);
            for(int i=c;i<N;i+=L) cnt[ct[i]]++;
            int idx[A]; for(int i=0;i<A;i++) idx[i]=i;
            for(int i=0;i<A;i++) for(int j=i+1;j<A;j++)
                if(cnt[idx[j]]>cnt[idx[i]]){int t=idx[i];idx[i]=idx[j];idx[j]=t;}
            for(int i=0;i<A;i++) alpha[c][idx[i]]=ORD[i];
            if(r){ for(int k=0;k<6;k++){int a=random()%A,b=random()%A;
                    int t=alpha[c][a];alpha[c][a]=alpha[c][b];alpha[c][b]=t;} }
        }
        double cur=score(),T=3.0;
        for(long it=0;it<iters;it++){
            int c=random()%L,a=random()%A,b=random()%A;
            if(a==b) continue;
            int t=alpha[c][a];alpha[c][a]=alpha[c][b];alpha[c][b]=t;
            double s=score();
            if(s>cur||((double)random()/RAND_MAX)<exp((s-cur)/T)) cur=s;
            else {t=alpha[c][a];alpha[c][a]=alpha[c][b];alpha[c][b]=t;}
            T*=0.9999992; if(T<0.015)T=0.015;
        }
        double s=score();
        if(s>best){best=s;memcpy(balpha,alpha,sizeof alpha);
            fprintf(stderr,"r=%d %.0f (%.3f/char) ",r,s,s/N);
            for(int i=0;i<70;i++) fputc('A'+pt[i],stderr);
            fprintf(stderr,"\n"); fflush(stderr);}
    }
    memcpy(alpha,balpha,sizeof alpha); score();
    printf("%.3f/char\n",best/N);
    for(int i=0;i<N;i++) putchar('A'+pt[i]);
    printf("\n");
    return 0;
}
