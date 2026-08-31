// GSMG small-blob oracle v3.
// Password modes, because the one known-good password on this page (Dualite)
// used RAW sha256 bytes, not the 64-char hex string everyone assumes:
//   0: sha256(X) as 64-char lowercase hex   1: sha256(X) as 32 raw bytes   2: X itself
// x 2 digests (sha256/md5) for EVP_BytesToKey = 6 trials per candidate.
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <openssl/sha.h>
#include <openssl/md5.h>
#include <openssl/aes.h>

static unsigned char SALT[8], CT[80];
static const char *HEX="0123456789abcdef";
static const char *MODE[4]={"sha256hex","sha256raw","literal","hexdecode"};

static void bytes_to_key(const unsigned char*pw,int pwlen,int md5,unsigned char*key,unsigned char*iv){
    unsigned char buf[96],prev[32]; int have=0,prevlen=0;
    while(have<48){
        if(md5){ MD5_CTX c; MD5_Init(&c);
            if(prevlen)MD5_Update(&c,prev,prevlen);
            MD5_Update(&c,pw,pwlen);MD5_Update(&c,SALT,8);MD5_Final(prev,&c);prevlen=16;
        } else { SHA256_CTX c; SHA256_Init(&c);
            if(prevlen)SHA256_Update(&c,prev,prevlen);
            SHA256_Update(&c,pw,pwlen);SHA256_Update(&c,SALT,8);SHA256_Final(prev,&c);prevlen=32; }
        int take=(have+prevlen>96)?96-have:prevlen;
        memcpy(buf+have,prev,take);have+=take;
    }
    memcpy(key,buf,32);memcpy(iv,buf+32,16);
}
static int check_pad(const AES_KEY*dk){
    unsigned char o[16]; AES_decrypt(CT+64,o,dk);
    for(int i=0;i<16;i++)o[i]^=CT[48+i];
    int p=o[15]; if(p<1||p>16)return 0;
    for(int i=16-p;i<16;i++) if(o[i]!=p) return 0;
    return p;
}
static void full(const AES_KEY*dk,const unsigned char*iv,unsigned char*pt){
    unsigned char prev[16]; memcpy(prev,iv,16);
    for(int b=0;b<5;b++){ AES_decrypt(CT+b*16,pt+b*16,dk);
        for(int i=0;i<16;i++)pt[b*16+i]^=prev[i];
        memcpy(prev,CT+b*16,16); }
}
int main(int argc,char**argv){
    const char*blobfile=argc>1?argv[1]:"blob.bin";
    FILE*f=fopen(blobfile,"rb"); unsigned char raw[96];
    if(!f||fread(raw,1,96,f)!=96){fprintf(stderr,"bad blob %s\n",blobfile);return 2;}
    fclose(f); memcpy(SALT,raw+8,8); memcpy(CT,raw+16,80);
    FILE*log=fopen(argc>2?argv[2]:"survivors3.log","w");
    long n=0,surv=0,hit=0;
    char line[8192]; unsigned char dg[32],key[32],iv[16],pt[80],pwbuf[8192];
    AES_KEY dk;
    while(fgets(line,sizeof line,stdin)){
        int len=strlen(line); while(len&&(line[len-1]=='\n'||line[len-1]=='\r'))line[--len]=0;
        if(!len) continue;
        SHA256((unsigned char*)line,len,dg);
        for(int mode=0;mode<4;mode++){
            int pwlen;
            if(mode==0){ for(int j=0;j<32;j++){pwbuf[2*j]=HEX[dg[j]>>4];pwbuf[2*j+1]=HEX[dg[j]&15];} pwlen=64; }
            else if(mode==1){ memcpy(pwbuf,dg,32); pwlen=32; }
            else if(mode==2){ memcpy(pwbuf,line,len); pwlen=len; }
            else { if(len<2||len%2) continue; int okhex=1;
                   for(int j=0;j<len;j++){char c=line[j]; if(!((c>='0'&&c<='9')||(c>='a'&&c<='f'))){okhex=0;break;}}
                   if(!okhex) continue;
                   for(int j=0;j<len/2;j++){int hi=line[2*j],lo=line[2*j+1];
                       hi=hi<='9'?hi-'0':hi-'a'+10; lo=lo<='9'?lo-'0':lo-'a'+10;
                       pwbuf[j]=(unsigned char)(hi*16+lo);} pwlen=len/2; }
            for(int d=0;d<2;d++){
                bytes_to_key(pwbuf,pwlen,d,key,iv);
                AES_set_decrypt_key(key,256,&dk);
                int p=check_pad(&dk); if(!p) continue;
                surv++; full(&dk,iv,pt);
                int body=80-p,pr=0;
                for(int i=0;i<body;i++){unsigned char c=pt[i]; if((c>=32&&c<127)||c==10||c==13||c==9)pr++;}
                double fr=body?(double)pr/body:0;
                fprintf(log,"%s\t%s\t%s\tpad=%d\tprintable=%.3f\n",line,MODE[mode],d?"md5":"sha256",p,fr);
                if(fr>=0.85){ hit++;
                    printf("\n*** PRINTABLE ***\ncandidate=%s\nmode=%s digest=%s pad=%d printable=%.1f%%\nplaintext=\"",
                           line,MODE[mode],d?"md5":"sha256",p,fr*100);
                    for(int i=0;i<body;i++) putchar((pt[i]>=32&&pt[i]<127)?pt[i]:'.');
                    printf("\"\n"); fflush(stdout);
                }
            }
        }
        n++;
    }
    fclose(log);
    fprintf(stderr,"blob=%s candidates=%ld trials=%ld survivors=%ld printable=%ld\n",
            blobfile,n,n*8,surv,hit);
    return hit?0:1;
}
