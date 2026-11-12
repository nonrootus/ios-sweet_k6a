"""Patch 0206: the GPU reads BGRA IOSurfaces in place (zero-copy), as on the K20 Pro port.

Since 0204/0205 (sRGB device tree) the surfaces CoreAnimation shows are BGRA. Each one used
as a texture was copied into the pinned GPU pool (full-screen ones: 11 MB, 8..30 ms) and
added up by the CPU every frame or two to notice changes. Mesa already asks for a surface
as a buffer (selector 0x7e, freedreno-darwin.patch); the kernel only knew the panel IDs.

- 512 MiB of GPU VA (0x60000000, L2 256..511 of SID0) gets 256 empty L3 tables before the
  context is installed, like the panel. A surface's own wired pages are entered there.
- A cleared range may still be in the SMMU's TLB: it is reused only after one TLBIASID +
  sync (sweet_smmu_context_invalidate), done when the window has no other room.
- Before a submission the kernel cleans the CPU cache of every imported surface it names
  whose seed moved, and of each at most once a frame (16 ms) otherwise, as Topaz does.
- Only one plane of BGRA with 64-byte rows in IOBufferMemoryDescriptor memory.
Submissions are synchronous and hold the client lock, so the GPU is idle at GEM_CLOSE.
"""
import re
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0206-sweet-a618-iosurface-zero-copy.patch'
FILES = {
    'bsd/dev/sweet_a618_render_pool.h': 'xnu/gpu/sweet_a618_render_pool.h',
    'bsd/dev/sweet_a618_render_pool.c': 'xnu/gpu/sweet_a618_render_pool.c',
    'bsd/dev/sweet_a618_address_space.c': 'xnu/gpu/sweet_a618_address_space.c',
    'bsd/dev/sweet_smmu_context.c': 'xnu/gpu/sweet_smmu_context.c',
    'bsd/dev/sweet_smmu_context.h': 'xnu/gpu/sweet_smmu_context.h',
    'iokit/Kernel/arm/sweet_a618_mapping.inc': 'xnu/gpu/sweet_a618_mapping.inc',
    'iokit/Kernel/arm/sweet_a618_renderer.inc': 'xnu/gpu/sweet_a618_renderer.inc',
    'iokit/Kernel/arm/sweet_a618_render_bridge.h': 'xnu/gpu/sweet_a618_render_bridge.h',
    'iokit/Kernel/arm/SweetAdreno.cpp': 'xnu/gpu/SweetAdreno.cpp',
}
base = {m: subprocess.check_output(GIT + ['show', 'HEAD:' + m], cwd=REPO).decode() for m in FILES.values()}
assert not any('\r' in v for v in base.values())
new = dict(base)


def edit(mirror, before, after):
    path = 'xnu/gpu/' + mirror
    assert new[path].count(before) == 1, (mirror, new[path].count(before), before[:80])
    new[path] = new[path].replace(before, after)


# ---- the window's constants and leaf functions (bsd/dev) -------------------------------------
edit('sweet_a618_render_pool.h', '#define SWEET_A618_PANEL_L2 192u\n', r'''#define SWEET_A618_PANEL_L2 192u

/* IOSurfaces the GPU reads in place: 512 MiB of GPU VA whose L3 tables are attached
 * empty before the context is installed. Leaves are entered and cleared at run time
 * (sweet_a618_renderer.inc); a cleared leaf needs a TLB invalidation before reuse. */
#define SWEET_A618_IMPORT_IOVA UINT32_C(0x60000000)
#define SWEET_A618_IMPORT_L2 256u
#define SWEET_A618_IMPORT_TABLES 256u
#define SWEET_A618_IMPORT_PAGES (SWEET_A618_IMPORT_TABLES * 512u)
''')
edit('sweet_a618_render_pool.h', '''int sweet_a618_panel_attach(const struct sweet_gpu_table_page base[3],
    const struct sweet_gpu_table_page tables[SWEET_A618_PANEL_TABLES]);
''', '''int sweet_a618_panel_attach(const struct sweet_gpu_table_page base[3],
    const struct sweet_gpu_table_page tables[SWEET_A618_PANEL_TABLES]);
/* Empty, zeroed, owned tables only; nothing is changed on failure. */
int sweet_a618_import_attach(const struct sweet_gpu_table_page base[3],
    const struct sweet_gpu_table_page tables[SWEET_A618_IMPORT_TABLES]);
int sweet_a618_import_check(const struct sweet_gpu_table_page base[3],
    const struct sweet_gpu_table_page tables[SWEET_A618_IMPORT_TABLES]);
/* Leaves for pages first.. of the window: only empty ones, all or none. The caller
 * completes the stores (dsb) before the GPU may use them. */
int sweet_a618_import_set(const struct sweet_gpu_table_page tables[SWEET_A618_IMPORT_TABLES],
    unsigned first, const uint64_t *physical, unsigned count);
void sweet_a618_import_clear(const struct sweet_gpu_table_page tables[SWEET_A618_IMPORT_TABLES],
    unsigned first, unsigned count);
''')
edit('sweet_a618_render_pool.c', '''_Static_assert(SWEET_A618_PANEL_PAGES <= SWEET_A618_PANEL_TABLES*TABLE_ENTRIES, "panel tables");
''', '''_Static_assert(SWEET_A618_PANEL_PAGES <= SWEET_A618_PANEL_TABLES*TABLE_ENTRIES, "panel tables");
_Static_assert((SWEET_A618_IMPORT_IOVA >> 30)==1u, "imports must share SID0 L1");
_Static_assert(((SWEET_A618_IMPORT_IOVA >> 21)&511u)==SWEET_A618_IMPORT_L2, "import L2 start");
_Static_assert(SWEET_A618_IMPORT_L2 >= SWEET_A618_PANEL_L2+SWEET_A618_PANEL_TABLES, "imports after the panel");
_Static_assert(SWEET_A618_IMPORT_L2+SWEET_A618_IMPORT_TABLES <= TABLE_ENTRIES, "imports inside one L2 table");
''')
edit('sweet_a618_render_pool.c', '''{
    return valid(base,extra,physical,1);
}
''', r'''{
    return valid(base,extra,physical,1);
}

int sweet_a618_import_attach(const struct sweet_gpu_table_page base[3],
    const struct sweet_gpu_table_page tables[SWEET_A618_IMPORT_TABLES])
{
    if (!base || !tables || !base[1].cpu) return -1;
    for (unsigned t = 0; t < SWEET_A618_IMPORT_TABLES; ++t) {
        uint64_t descriptor;
        if (!tables[t].cpu || ((uintptr_t)tables[t].cpu & (PAGE_BYTES-1)) ||
            sweet_gpu_pte_table(tables[t].pa,&descriptor) ||
            base[1].cpu[SWEET_A618_IMPORT_L2+t]) return -1;
        for (unsigned j = 0; j < 3; ++j)
            if (tables[t].pa == base[j].pa) return -1;
        for (unsigned leaf = 0; leaf < TABLE_ENTRIES; ++leaf)
            if (tables[t].cpu[leaf]) return -1;
    }
    /* Empty children before the L2 descriptors; the caller cleans them all. */
    for (unsigned t = 0; t < SWEET_A618_IMPORT_TABLES; ++t)
        base[1].cpu[SWEET_A618_IMPORT_L2+t] = tables[t].pa | 3u;
    return 0;
}

int sweet_a618_import_check(const struct sweet_gpu_table_page base[3],
    const struct sweet_gpu_table_page tables[SWEET_A618_IMPORT_TABLES])
{
    if (!base || !tables || !base[1].cpu) return -1;
    for (unsigned t = 0; t < SWEET_A618_IMPORT_TABLES; ++t)
        if (base[1].cpu[SWEET_A618_IMPORT_L2+t] != (tables[t].pa | 3u)) return -1;
    return 0;
}

int sweet_a618_import_set(const struct sweet_gpu_table_page tables[SWEET_A618_IMPORT_TABLES],
    unsigned first, const uint64_t *physical, unsigned count)
{
    if (!tables || !physical || !count || first >= SWEET_A618_IMPORT_PAGES ||
        count > SWEET_A618_IMPORT_PAGES-first) return -1;
    for (unsigned i = 0; i < count; ++i) {
        const unsigned page = first+i;
        uint64_t pte;
        if (!tables[page/TABLE_ENTRIES].cpu || tables[page/TABLE_ENTRIES].cpu[page%TABLE_ENTRIES] ||
            sweet_gpu_pte_page_access(physical[i],0,0,&pte)) return -1;
    }
    /* No fallible step after the first store. Same attributes as the pool: never execute. */
    for (unsigned i = 0; i < count; ++i) {
        const unsigned page = first+i;
        uint64_t pte;
        (void)sweet_gpu_pte_page_access(physical[i],0,0,&pte);
        tables[page/TABLE_ENTRIES].cpu[page%TABLE_ENTRIES] = pte | (UINT64_C(3)<<53);
    }
    return 0;
}

void sweet_a618_import_clear(const struct sweet_gpu_table_page tables[SWEET_A618_IMPORT_TABLES],
    unsigned first, unsigned count)
{
    if (!tables || first >= SWEET_A618_IMPORT_PAGES || count > SWEET_A618_IMPORT_PAGES-first) return;
    for (unsigned i = 0; i < count; ++i) {
        const unsigned page = first+i;
        if (tables[page/TABLE_ENTRIES].cpu)
            tables[page/TABLE_ENTRIES].cpu[page%TABLE_ENTRIES] = 0;
    }
}
''')
edit('sweet_a618_address_space.c',
     '''        if(level==1 && i>=SWEET_A618_PANEL_L2 && i<SWEET_A618_PANEL_L2+SWEET_A618_PANEL_TABLES)continue;
''', '''        if(level==1 && i>=SWEET_A618_PANEL_L2 && i<SWEET_A618_PANEL_L2+SWEET_A618_PANEL_TABLES)continue;
        /* (the import window: sweet_a618_import_check, when it is attached) */
        if(level==1 && i>=SWEET_A618_IMPORT_L2 && i<SWEET_A618_IMPORT_L2+SWEET_A618_IMPORT_TABLES)continue;
''')
edit('sweet_smmu_context.h', 'int sweet_smmu_context_remove(struct sweet_smmu_context *);\n',
     '''/* TLBIASID and sync of an ACTIVE context, for leaves cleared while it is live. The
 * caller serializes with every other user of this context's registers. A failure
 * leaves the TLB state unknown: stop using the context's address space. */
int sweet_smmu_context_invalidate(struct sweet_smmu_context *);
int sweet_smmu_context_remove(struct sweet_smmu_context *);
''')
new['xnu/gpu/sweet_smmu_context.c'] += '''
int sweet_smmu_context_invalidate(struct sweet_smmu_context *c)
{
    if (!c || c->state != SWEET_SMMU_CONTEXT_ACTIVE) return SWEET_SMMU_CONTEXT_INVALID;
    return invalidate(c);
}
'''

# ---- cold attach and run-time leaf changes (iokit, in sweet_gpu_gmu_start.cpp) ---------------
edit('sweet_a618_mapping.inc', '''    bool panel_ready;
''', '''    bool panel_ready;
    sweet_gpu_memory *import_tables_memory;
    sweet_gpu_table_page import_tables[SWEET_A618_IMPORT_TABLES];
    bool import_ready;
''')
edit('sweet_a618_mapping.inc', '''#ifdef KERNEL
    return m.render_ready ?
''', '''#ifdef KERNEL
    if(m.import_ready && sweet_a618_import_check(m.tables,m.import_tables))return -1;
    return m.render_ready ?
''')
edit('sweet_a618_mapping.inc', '''            m.render_ready=true;
''', r'''            /* IOSurfaces read in place: empty leaf tables now, leaves at run time. Optional. */
            m.import_tables_memory=sweet_gpu_memory_create_nc(SWEET_A618_IMPORT_TABLES);
            bool imports=m.import_tables_memory!=nullptr;
            for(unsigned i=0;imports && i<SWEET_A618_IMPORT_TABLES;i++){
                void *cpu=nullptr;uint64_t pa=0;
                if(sweet_gpu_memory_page(m.import_tables_memory,i,&cpu,&pa))imports=false;
                else m.import_tables[i]={static_cast<uint64_t *>(cpu),pa};
            }
            if(imports && !sweet_a618_import_attach(m.tables,m.import_tables)){
                for(unsigned i=0;i<SWEET_A618_IMPORT_TABLES;i++)
                    if(sweet_gpu_memory_clean(m.import_tables_memory,i))return -5;
                m.import_ready=true;
                IOLog("SWEET CA: IOSurface import window at GPU VA %x, %u MiB\n",
                    SWEET_A618_IMPORT_IOVA,SWEET_A618_IMPORT_PAGES>>8);
            }else{
                IOLog("SWEET CA: IOSurface import window unavailable; surfaces stay copied\n");
            }
            m.render_ready=true;
''')
edit('sweet_a618_renderer.inc', '''    IOLockUnlock(a618_renderer.lock);
    return rc;
}
''', r'''    IOLockUnlock(a618_renderer.lock);
    return rc;
}

/*
 * The import window (SweetAdreno.cpp). Leaves only go from invalid to valid without TLB
 * work; a cleared range stays out of use until sweet_a618_import_invalidate.
 */
extern "C" bool sweet_a618_import_ready(void)
{
    return sweet_a618_render_ready() && a618_mapping.import_ready;
}

extern "C" int sweet_a618_import_map(unsigned first,const uint64_t *physical,unsigned count)
{
    if(!sweet_a618_import_ready() ||
        sweet_a618_import_set(a618_mapping.import_tables,first,physical,count))return -1;
    __asm__ volatile("dsb sy" ::: "memory"); // Normal-NC tables: the walker sees them after this.
    return 0;
}

extern "C" void sweet_a618_import_unmap(unsigned first,unsigned count)
{
    if(!a618_mapping.import_ready)return;
    sweet_a618_import_clear(a618_mapping.import_tables,first,count);
    __asm__ volatile("dsb sy" ::: "memory");
}

extern "C" int sweet_a618_import_invalidate(void)
{
    if(!sweet_a618_import_ready())return -1;
    IOLockLock(a618_renderer.lock); // No submission is running while the TLB is emptied.
    const int rc=sweet_smmu_context_invalidate(&a618_mapping.context);
    if(rc){
        __atomic_store_n(&a618_renderer.poisoned,true,__ATOMIC_RELEASE);
        IOLog("SWEET CA: SMMU invalidation failed rc=%d; GPU submissions stopped\n",rc);
    }
    IOLockUnlock(a618_renderer.lock);
    static unsigned logs;
    if(!rc && logs++<8)IOLog("SWEET CA: SMMU TLB invalidated before import space is reused\n");
    return rc;
}
''')
edit('sweet_a618_render_bridge.h', '''extern "C" bool sweet_a618_direct_take(uint32_t surface);
''', '''extern "C" bool sweet_a618_direct_take(uint32_t surface);
/* IOSurfaces read by the GPU in place: pages of the import window (render_pool.h). */
extern "C" bool sweet_a618_import_ready(void);
extern "C" int sweet_a618_import_map(unsigned first, const uint64_t *physical, unsigned count);
extern "C" void sweet_a618_import_unmap(unsigned first, unsigned count);
extern "C" int sweet_a618_import_invalidate(void);
''')

# ---- the user client ------------------------------------------------------------------------
A = 'SweetAdreno.cpp'
edit(A, ''' * GPU memory is a single pre-pinned Normal-NC pool. No live SMMU edits,
 * external IOSurface import, DMA teardown or GPU reset is provided here. */''',
     ''' * GPU memory is a single pre-pinned Normal-NC pool; BGRA IOSurfaces are read in place
 * through the import window (importSurface). No DMA teardown or GPU reset here. */''')
edit(A, '''extern "C" {
#include <arm/machine_routines.h>
}
''', '''extern "C" {
#include <arm/machine_routines.h>
#include <arm/caches_internal.h>
}
#include <mach/mach_time.h>
#include "SweetSurface.h"
''')
edit(A, '''struct sweet_bo { IOMemoryDescriptor *memory;uint64_t size,iova;uint32_t flags; };
''', r'''struct sweet_bo {
    IOMemoryDescriptor *memory;uint64_t size,iova;uint32_t flags;
    /* An imported IOSurface: its pages in the import window, and when the CPU cache was last cleaned. */
    SweetSurface *surface;unsigned import_first,import_pages;uint32_t seed;uint64_t flushed;
};

/*
 * IOSurfaces the GPU reads in place. A cleared range may still be in the SMMU's TLB, so it is
 * not used again before one invalidation of the context, done only when the window has no
 * other room. Shared by all clients under pool_lock; lock order: client lock, pool_lock,
 * the renderer's submit lock.
 */
static constexpr unsigned kImportPages=SWEET_A618_IMPORT_PAGES;
static uint64_t import_used[kImportPages/64],import_stale[kImportPages/64];
static unsigned import_count,import_logs,import_flushes;
static uint64_t import_flushed_bytes,import_flush_ticks;

static bool import_taken(unsigned page)
{
    return ((import_used[page/64]|import_stale[page/64])>>(page%64))&1u;
}

/* Caller holds pool_lock. */
static int import_reserve(unsigned pages)
{
    for(unsigned pass=0;pass<2;pass++){
        for(unsigned first=0;first+pages<=kImportPages;){
            unsigned run=0;
            while(run<pages && !import_taken(first+run))run++;
            if(run==pages){
                for(unsigned i=0;i<pages;i++)
                    import_used[(first+i)/64]|=UINT64_C(1)<<((first+i)%64);
                import_count++;
                return static_cast<int>(first);
            }
            first+=run+1;
        }
        bool stale=false;
        for(unsigned i=0;i<kImportPages/64;i++)stale|=import_stale[i]!=0;
        if(pass || !stale || sweet_a618_import_invalidate())break;
        bzero(import_stale,sizeof(import_stale));
    }
    return -1;
}

static void import_forget(unsigned first,unsigned pages,bool stale)
{
    IOLockLock(pool_lock);
    for(unsigned i=0;i<pages;i++){
        const unsigned page=first+i;
        import_used[page/64]&=~(UINT64_C(1)<<(page%64));
        if(stale)import_stale[page/64]|=UINT64_C(1)<<(page%64);
    }
    import_count--;
    IOLockUnlock(pool_lock);
}

static uint32_t import_seed(SweetSurface *surface)
{
    return *reinterpret_cast<volatile uint32_t *>(static_cast<uint8_t *>(surface->state->getBytesNoCopy())+0xc);
}

/* With the client lock held, so no submission is running: the GPU no longer reads it. */
static void import_release(sweet_bo &bo)
{
    sweet_a618_import_unmap(bo.import_first,bo.import_pages);
    import_forget(bo.import_first,bo.import_pages,true);
    bo.memory->complete();
    bo.surface->release();
    bo.surface=nullptr;
}

/*
 * The GPU reads an imported surface from memory; what the CPU wrote may still be in its
 * cache. Cleaned when the surface's seed has moved (a writer locks it), and otherwise at
 * most once a frame, since not every writer says so (Topaz does the same).
 */
static void import_flush(sweet_bo *bo)
{
    static uint64_t again;
    if(!again)nanoseconds_to_absolutetime(16*NSEC_PER_MSEC,&again);
    const uint32_t seed=import_seed(bo->surface);
    const uint64_t began=mach_absolute_time();
    if(seed==bo->seed && began-bo->flushed<again)return;
    auto *buffer=static_cast<IOBufferMemoryDescriptor *>(bo->memory);
    flush_dcache(reinterpret_cast<vm_offset_t>(buffer->getBytesNoCopy()),static_cast<unsigned>(bo->size),FALSE);
    bo->seed=seed;
    bo->flushed=mach_absolute_time();
    import_flushed_bytes+=bo->size;
    import_flush_ticks+=bo->flushed-began;
    if(++import_flushes%1024==0){
        uint64_t ns=0;
        absolutetime_to_nanoseconds(import_flush_ticks/1024,&ns);
        IOLog("SWEET CA: imported surfaces cleaned %u times, %llu MB in the last 1024, %llu us each, %u imported now\n",
            import_flushes,import_flushed_bytes>>20,ns/1000,import_count);
        import_flushed_bytes=import_flush_ticks=0;
    }
}
''')
edit(A, '''    IOReturn surfaceBuffer(redwood_surface *request);
''', '''    IOReturn surfaceBuffer(redwood_surface *request);
    IOReturn importSurface(redwood_surface *request);
    void dropBO(sweet_bo *bo);
''')
edit(A, '''        auto *memory=bos[i].memory;
        bos[i].memory=nullptr;
        if(memory)memory->release();
''', '''        if(bos[i].memory)dropBO(&bos[i]);
''')
edit(A, '''        sweet_bo *bo=lookup(sb[i].handle);
        if(!bo){result=kIOReturnBadArgument;goto unlock;}
''', '''        sweet_bo *bo=lookup(sb[i].handle);
        if(!bo){result=kIOReturnBadArgument;goto unlock;}
        if(bo->surface)import_flush(bo);
''')
edit(A, '''    if(id<kDirectShadowEven || id>kDirectPanelOdd)return kIOReturnUnsupported;
''', '''    if(id<kDirectShadowEven || id>kDirectPanelOdd)return importSurface(request);
''')
edit(A, '''IOReturn SweetAdrenoUserClient::direct(sweet_direct_request *request)
{''', r'''/* With the client lock held. */
void SweetAdrenoUserClient::dropBO(sweet_bo *bo)
{
    auto *memory=bo->memory;
    if(bo->surface)import_release(*bo);
    bo->memory=nullptr;
    memory->release();
}

/*
 * An IOSurface as a buffer the GPU reads in place: what Mesa's freedreno-darwin.patch asks
 * for. One plane of BGRA in wired kernel memory (IOBufferMemoryDescriptor), rows a multiple
 * of the GPU's 64-byte pitch; anything else stays a copy (kIOReturnUnsupported).
 */
IOReturn SweetAdrenoUserClient::importSurface(redwood_surface *request)
{
    SweetSurface *s=sweet_surface_copy(request->surface);
    if(!s)return kIOReturnNotFound;
    auto *buffer=OSDynamicCast(IOBufferMemoryDescriptor,s->memory);
    const uint64_t bytes=buffer ? buffer->getLength()&~UINT64_C(4095):0;
    const uint64_t used=static_cast<uint64_t>(s->offset)+static_cast<uint64_t>(s->bytesPerRow)*s->height;
    if(!buffer || !s->state || s->pixelFormat!=0x42475241u || s->planeCount || s->bytesPerElement!=4 ||
        s->elementWidth!=1 || s->elementHeight!=1 || !s->width || !s->height || (s->bytesPerRow&63u) ||
        s->bytesPerRow<s->width*4u || !bytes || used>bytes || bytes>static_cast<uint64_t>(kImportPages)*4096u){
        s->release();
        return kIOReturnUnsupported;
    }
    request->size=bytes;
    request->offset=s->offset;
    request->row_bytes=s->bytesPerRow;
    request->width=s->width;
    request->height=s->height;
    request->pixel_format=s->pixelFormat;
    request->planes=0;
    if(request->handle==kDirectDescribe){
        request->handle=0;
        s->release();
        return kIOReturnSuccess;
    }
    if(!sweet_a618_import_ready()){
        s->release();
        return kIOReturnUnsupported;
    }
    /* A surface this client has already is the same buffer again, as Mesa's handle table expects. */
    IOLockLock(lock);
    for(unsigned i=0;i<kHandles;i++){
        if(bos[i].memory && bos[i].surface==s){
            request->handle=i+1;
            IOLockUnlock(lock);
            s->release();
            return kIOReturnSuccess;
        }
    }
    IOLockUnlock(lock);

    const unsigned pages=static_cast<unsigned>(bytes/4096u);
    const size_t list_bytes=pages*sizeof(uint64_t);
    auto *physical=static_cast<uint64_t *>(IOMallocData(list_bytes));
    if(!physical || buffer->prepare()!=kIOReturnSuccess){
        if(physical)IOFreeData(physical,list_bytes);
        s->release();
        return kIOReturnNoMemory;
    }
    bool ok=true;
    for(unsigned i=0;ok && i<pages;i++){
        IOByteCount length=0;
        const addr64_t page=buffer->getPhysicalSegment(static_cast<IOByteCount>(i)*4096u,&length,kIOMemoryMapperNone);
        ok=page && !(page&4095u) && length>=4096u;
        physical[i]=page;
    }
    IOLockLock(pool_lock);
    const int first=ok ? import_reserve(pages):-1;
    IOLockUnlock(pool_lock);
    const bool mapped=first>=0 && !sweet_a618_import_map(static_cast<unsigned>(first),physical,pages);
    IOFreeData(physical,list_bytes);
    if(!mapped){
        if(first>=0)import_forget(static_cast<unsigned>(first),pages,false);
        buffer->complete();
        static unsigned refused;
        if(refused++<8)IOLog("SWEET CA: IOSurface %u (%u pages) not imported: %s\n",request->surface,pages,
            !ok ? "no physical pages" : first<0 ? "no room in the window" : "leaves refused");
        s->release();
        return kIOReturnNoMemory;
    }
    /* What the CPU wrote is in memory before the GPU first reads it. */
    flush_dcache(reinterpret_cast<vm_offset_t>(buffer->getBytesNoCopy()),static_cast<unsigned>(bytes),FALSE);
    buffer->retain();
    sweet_bo bo={buffer,bytes,SWEET_A618_IMPORT_IOVA+static_cast<uint64_t>(first)*4096u,0,
        s,static_cast<unsigned>(first),pages,import_seed(s),mach_absolute_time()};
    unsigned handle=0;
    IOLockLock(lock);
    for(unsigned i=0;i<kHandles;i++){
        unsigned candidate=(next_handle+i)%kHandles;
        if(!bos[candidate].memory){handle=candidate+1;break;}
    }
    if(handle){
        bos[handle-1]=bo;
        next_handle=handle%kHandles;
    }else{
        dropBO(&bo);
    }
    IOLockUnlock(lock);
    if(!handle)return kIOReturnNoMemory;
    request->handle=handle;
    if(import_logs<8){
        import_logs++;
        IOLog("SWEET CA: IOSurface %u %ux%u read in place at GPU VA %llx, %u pages, %u imported\n",
            request->surface,s->width,s->height,static_cast<unsigned long long>(bo.iova),pages,import_count);
    }
    return kIOReturnSuccess;
}

IOReturn SweetAdrenoUserClient::direct(sweet_direct_request *request)
{''')
edit(A, '''        if(bo){
            auto *memory=bo->memory;
            bo->memory=nullptr;
            memory->release();
        }else result=kIOReturnBadArgument;
''', '''        if(bo)dropBO(bo);
        else result=kIOReturnBadArgument;
''')

for mirror in FILES.values():
    (REPO / mirror).write_bytes(new[mirror].encode())

with tempfile.TemporaryDirectory(prefix='make-0206-', dir='D:/ios-sweet/build') as scratch:
    work = Path(scratch)
    for side, data in (('a', base), ('b', new)):
        for target, mirror in FILES.items():
            path = work / side / target
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data[mirror].encode())
    done = subprocess.run(GIT + ['diff', '--no-index', '--no-color', '--no-prefix', '-U3', 'a', 'b'], cwd=work, capture_output=True)
    assert done.returncode == 1, done.stderr
    text = re.sub(r'^diff --git .*\n(index .*\n)?', '', done.stdout.decode(), flags=re.M)
    assert text.startswith('--- a/') and '\r' not in text
    output = REPO / 'xnu/patches' / NAME
    output.write_bytes(text.encode())
    check = work / 'check'
    for target, mirror in FILES.items():
        path = check / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base[mirror].encode())
    subprocess.run(GIT + ['apply', str(output)], cwd=check, check=True)
    assert all((check / t).read_bytes() == new[m].encode() for t, m in FILES.items())
    # Earlier patches whose reversal on these files no longer applies: CI must exclude them there.
    script = REPO / 'tools/check-sweet-patch-reversal.sh'
    lines = script.read_bytes().decode().replace('\r\n', '\n').split('\n')
    changed = []
    for at, line in enumerate(lines):
        found = re.search(r'xnu/patches/(\d{4}-[^"]+\.patch)', line)
        if 'apply --reverse' not in line or not found:
            continue
        patch = REPO / 'xnu/patches' / found.group(1)
        touched = {l.split('\t')[-1] for l in subprocess.check_output(GIT + ['apply', '--numstat', str(patch)], cwd=check, text=True).splitlines()}
        for target in sorted(touched & set(FILES)):
            if '--exclude=' + target in line:
                continue
            done = subprocess.run(GIT + ['apply', '--reverse', '--check', '--include=' + target, str(patch)], cwd=check, capture_output=True)
            if done.returncode != 0:
                line = line.replace(' --check ', ' --check --exclude=' + target + ' ', 1)
                changed.append((found.group(1), target))
        lines[at] = line
    subprocess.run(GIT + ['apply', '--reverse', str(output)], cwd=check, check=True)
print(NAME, len(text.splitlines()), 'lines, forward and reverse verified')
print('excludes added:', changed)
assert not any(NAME in line for line in lines)
last = max(i for i, line in enumerate(lines) if 'apply --reverse --check' in line or 'grep -F' in line)
lines.insert(last + 1, '# 0206: BGRA IOSurfaces read by the GPU in place (import window, TLB invalidation, cache cleaning).')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())

verify = REPO / 'tools/verify-gmu-service-patch.py'
source = verify.read_bytes().decode().replace('\r\n', '\n')
anchor = "PATCHES += (('xnu/patches/0203-sweet-a618-gpu-thread-on-a76.patch', {'iokit/Kernel/arm/SweetAdreno.cpp'}),)\n"
assert source.count(anchor) == 1 and NAME not in source
targets = ', '.join("'" + t + "'" for t in FILES)
source = source.replace(anchor, anchor + "PATCHES += (('xnu/patches/" + NAME + "', {" + targets + "}),)\n")
verify.write_bytes(source.encode())
print('verify list and reversal script updated')
