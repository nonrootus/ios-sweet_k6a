#include "sweet_gpu_bundle.h"
#include <string.h>
#define HEADER 24u
#define ENTRY 80u
#define PAGE 4096u
#define LIMIT (1024u*1024u)
static uint32_t le32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint64_t le64(const uint8_t *p){return (uint64_t)le32(p)|((uint64_t)le32(p+4)<<32);}
int sweet_gpu_bundle_parse(const void *buffer,size_t size,struct sweet_gpu_blob out[SWEET_GPU_BUNDLE_FILES]){
 static const char *const names[]={"a618_gmu.bin","a630_sqe.fw","a615_zap.mdt","a615_zap.b02"};
 const uint8_t *b=buffer;struct sweet_gpu_blob tmp[SWEET_GPU_BUNDLE_FILES];uint64_t end=PAGE;unsigned i;
 if(!b||!out||size<PAGE||memcmp(b,"SWEETGPU",8)||le32(b+8)!=1||le32(b+12)!=SWEET_GPU_BUNDLE_FILES||le64(b+16)!=size)return -1;
 for(i=0;i<SWEET_GPU_BUNDLE_FILES;i++){
  const uint8_t *e=b+HEADER+i*ENTRY; size_t n=strlen(names[i]);uint64_t off=le64(e+32),len=le64(e+40);unsigned j;
  if(memcmp(e,names[i],n))return -1;
  for(j=(unsigned)n;j<32;j++)if(e[j])return -1;
  if(off!=end||!len||len>LIMIT||off>size||len>(uint64_t)size-off)return -1;
  tmp[i].data=b+(size_t)off;tmp[i].size=(size_t)len;tmp[i].sha256=e+48;
  end=(off+len+PAGE-1)&~(uint64_t)(PAGE-1);
 }
 if(end!=size)return -1;
 memcpy(out,tmp,sizeof(tmp));return 0;
}
