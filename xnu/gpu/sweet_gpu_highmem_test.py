#!/usr/bin/env python3
"""Regression for the actual patched pmap cache-sync function's PA arithmetic.

Usage: python3 sweet_gpu_highmem_test.py PATCHED_XNU_TREE BUILD_DIRECTORY
Compiles the extracted function with a recording flush stub; no physical access.
"""
from pathlib import Path
import re
import subprocess
import sys

tree=Path(sys.argv[1]).resolve(strict=True)
build=Path(sys.argv[2]).resolve(strict=True)
text=(tree/'osfmk/arm/pmap/pmap.c').read_text()
function=re.search(r'void\s+pmap_sync_page_attributes_phys\(\s*ppnum_t pp\)\s*\{[^}]+\}',text).group()
source='''#include <stdint.h>
#include <assert.h>
typedef uint32_t ppnum_t;
typedef uint64_t vm_offset_t;
#define PAGE_SHIFT 14
#define PAGE_SIZE (1u << PAGE_SHIFT)
#define TRUE 1
#define ptoa_64(x) ((uint64_t)(x) << PAGE_SHIFT)
static uint64_t seen;
static void flush_dcache(vm_offset_t pa,unsigned n,int phys) {
    assert(n==PAGE_SIZE && phys==TRUE); seen=pa;
}
'''+function+'''
int main(void) {
    const uint64_t addresses[]={0x4000ull,0xffffc000ull,0x100000000ull,0x100004000ull,0xffffff000ull&~0x3fffull};
    for(unsigned i=0;i<sizeof(addresses)/sizeof(addresses[0]);++i) {
        pmap_sync_page_attributes_phys((ppnum_t)(addresses[i]>>PAGE_SHIFT));
        assert(seen==addresses[i]);
    }
}
'''
out=build/'highmem-cache-sync-test.c'
out.write_text(source)
exe=build/'highmem-cache-sync-test'
subprocess.run(['gcc','-std=c11','-Wall','-Werror','-fsanitize=undefined',str(out),'-o',str(exe)],check=True)
subprocess.run([str(exe)],check=True)
print('PASS: actual patched cache-sync function preserves PA across 4GiB and near36-bit limit')
