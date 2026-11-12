#include "sweet_gpu_bundle.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){fprintf(stderr,"failed line %d\n",__LINE__);return 1;}}while(0)
int main(int argc,char **argv){FILE *f;long n;unsigned char *b;struct sweet_gpu_blob o[4],before[4];
 if(argc!=2)return 2; f=fopen(argv[1],"rb");if(!f||fseek(f,0,SEEK_END)||(n=ftell(f))<0||fseek(f,0,SEEK_SET))return 2;
 b=malloc((size_t)n);if(!b||fread(b,1,(size_t)n,f)!=(size_t)n)return 2;fclose(f);
 CHECK(!sweet_gpu_bundle_parse(b,n,o));CHECK(o[0].size==32768&&o[1].size==32136&&o[0].data==b+4096);
 memset(before,0xa5,sizeof(before));memcpy(o,before,sizeof(o));b[24+32]=1;
 CHECK(sweet_gpu_bundle_parse(b,n,o));CHECK(!memcmp(o,before,sizeof(o)));b[24+32]=0;
 CHECK(sweet_gpu_bundle_parse(b,4095,o));b[8]=2;CHECK(sweet_gpu_bundle_parse(b,n,o));free(b);puts("GPU bundle parsing checks passed");return 0;}
