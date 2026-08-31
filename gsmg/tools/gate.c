// GSMG small-blob oracle v2: reveals plaintext on every PKCS7 pass.
// candidate -> sha256 hex password -> EVP_BytesToKey{sha256,md5} -> AES-256-CBC -> PKCS7
// -> full decrypt, printable ratio. Logs all survivors; flags printable ones.
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <openssl/sha.h>
#include <openssl/md5.h>
#include <openssl/aes.h>

static const unsigned char SALT[8]={0x3a,0xb5,0x85,0x34,0x85,0x52,0x41,0x5d};
static unsigned char CT[80];
static const char *HEX="0123456789abcdef";

static void bytes_to_key(const char*pw,int pwlen,int md5,unsigned char*key,unsigned char*iv){
    unsigned char buf[96]; int have=0; unsigned char prev[32]; int prevlen=0;
    while(have<48){
        if(md5){ MD5_CTX c; MD5_Init(&c);
            if(prevlen) MD5_Update(&c,prev,prevlen);
            MD5_Update(&c,pw,pwlen); MD5_Update(&c,SALT,8); MD5_Final(prev,&c); prevlen=16;
        } else { SHA256_CTX c; SHA256_Init(&c);
            if(prevlen) SHA256_Update(&c,prev,prevlen);
            SHA256_Update(&c,pw,pwlen); SHA256_Update(&c,SALT,8); SHA256_Final(prev,&c); prevlen=32; }
        int take=(have+prevlen>96)?96-have:prevlen;
        memcpy(buf+have,prev,take); have+=take;
    }
    memcpy(key,buf,32); memcpy(iv,buf+32,16);
}
static int check_pad(const AES_KEY*dk){
    unsigned char out[16]; AES_decrypt(CT+64,out,dk);
    for(int i=0;i<16;i++) out[i]^=CT[48+i];
    int p=out[15]; if(p<1||p>16) return 0;
    for(int i=16-p;i<16;i++) if(out[i]!=p) return 0;
    return p;
}
static void full_decrypt(const AES_KEY*dk,const unsigned char*iv,unsigned char*pt){
    unsigned char prev[16]; memcpy(prev,iv,16);
    for(int b=0;b<5;b++){
        AES_decrypt(CT+b*16,pt+b*16,dk);
        for(int i=0;i<16;i++) pt[b*16+i]^=prev[i];
        memcpy(prev,CT+b*16,16);
    }
}
int main(int argc,char**argv){
    FILE*f=fopen("blob.bin","rb"); unsigned char raw[96];
    if(!f||fread(raw,1,96,f)!=96){fprintf(stderr,"blob.bin missing\n");return 2;}
    fclose(f); memcpy(CT,raw+16,80);
    FILE*log=fopen(argc>1?argv[1]:"survivors.log","w");
    long n=0,surv=0,interesting=0;
    char line[8192]; unsigned char dg[32],key[32],iv[16],pt[80];
    char pw[65]; pw[64]=0; AES_KEY dk;
    while(fgets(line,sizeof line,stdin)){
        int len=strlen(line); while(len&&(line[len-1]=='\n'||line[len-1]=='\r'))line[--len]=0;
        if(!len) continue;
        SHA256((unsigned char*)line,len,dg);
        for(int j=0;j<32;j++){pw[2*j]=HEX[dg[j]>>4];pw[2*j+1]=HEX[dg[j]&15];}
        for(int d=0;d<2;d++){
            bytes_to_key(pw,64,d,key,iv);
            AES_set_decrypt_key(key,256,&dk);
            int p=check_pad(&dk);
            if(!p) continue;
            surv++;
            full_decrypt(&dk,iv,pt);
            int body=80-p, pr=0;
            for(int i=0;i<body;i++){unsigned char c=pt[i]; if((c>=32&&c<127)||c==10||c==13||c==9) pr++;}
            double frac=body?(double)pr/body:0;
            fprintf(log,"%s\t%s\tpad=%d\tprintable=%.3f\t",line,d?"md5":"sha256",p,frac);
            for(int i=0;i<body;i++) fprintf(log,"%02x",pt[i]);
            fprintf(log,"\n");
            if(frac>=0.85){
                interesting++;
                printf("\n*** PRINTABLE PLAINTEXT ***\ncandidate = %s\ndigest=%s pad=%d printable=%.1f%%\nplaintext = \"",line,d?"md5":"sha256",p,frac*100);
                for(int i=0;i<body;i++) putchar((pt[i]>=32&&pt[i]<127)?pt[i]:'.');
                printf("\"\n"); fflush(stdout);
            }
        }
        n++;
    }
    fclose(log);
    fprintf(stderr,"candidates=%ld trials=%ld pkcs7_survivors=%ld printable_hits=%ld\n",n,n*2,surv,interesting);
    return interesting?0:1;
}
