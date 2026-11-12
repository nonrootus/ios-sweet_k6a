"""Patch 0211: USB console and USB network at once, the network as RNDIS, which Windows drives itself.

sweetusb=4: one composite device (IADs) with the ACM console of sweetusb=3 on interfaces 0/1 and an
RNDIS network function on interfaces 2/3 (the class Android's USB tethering uses, E0/01/03, which
Windows 10 binds to its own Remote NDIS driver; CDC-ECM of sweetusb=2 needs a third-party driver
there). The PC shares its internet with Windows' Internet Connection Sharing, whose side of the link
is 192.168.137.1: in this mode ue0 is 192.168.137.2/24. RNDIS control messages travel as
SEND_ENCAPSULATED_COMMAND / GET_ENCAPSULATED_RESPONSE on endpoint 0 with RESPONSE_AVAILABLE on
the interrupt endpoint; each Ethernet frame on the bulk endpoints has a 44-byte RNDIS packet header.
Message and OID layout follow the RNDIS specification as implemented by Linux's
drivers/usb/gadget/function/rndis.c. pid.codes 1209:0003 is a private test ID.
Base: CI build tree 40478936434 plus 0180 for bsd/dev/sweet_usb.c.
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
TREE = Path('D:/ios-sweet/build/xnu-buildtree-40478936434/xnu')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0211-sweet-usb-console-and-rndis.patch'
USB = 'bsd/dev/sweet_usb.c'

with tempfile.TemporaryDirectory(prefix='make-0211-', dir='D:/ios-sweet/build') as scratch:
    work = Path(scratch)
    (work / USB).parent.mkdir(parents=True)
    shutil.copyfile(TREE / USB, work / USB)
    patch = work / '0180.patch'
    patch.write_bytes(subprocess.check_output(GIT + ['show', 'HEAD:xnu/patches/0180-sweet-usb-console-and-b3a8-evidence.patch'], cwd=REPO))
    subprocess.run(GIT + ['apply', '--include=' + USB, patch.name], cwd=work, check=True)
    base = (work / USB).read_bytes().decode()
assert '\r' not in base
new = base


def edit(before, after, count=1):
    global new
    assert new.count(before) == count, (new.count(before), before[:90])
    new = new.replace(before, after)


edit('''static void sweet_usb_gadget_start(vm_offset_t dwc, bool serial);
''', '''static void sweet_usb_gadget_start(vm_offset_t dwc, int mode);
''')
edit('''	/* sweetusb=0 off, 1 probe, 2 ECM, 3 ACM console output. */
''', '''	/* sweetusb=0 off, 1 probe, 2 ECM, 3 ACM console output, 4 ACM console + RNDIS network. */
''')
edit('''	if (enabled == 2 || enabled == 3) {
		sweet_usb_gadget_start(dwc, enabled == 3);
	}
''', '''	if (enabled >= 2 && enabled <= 4) {
		sweet_usb_gadget_start(dwc, enabled);
	}
''')
edit('''#define UD_TX           0x2800          /* one frame to send */
''', '''#define UD_TX           0x2800          /* one frame to send */
/* sweetusb=4: the RNDIS function's own endpoints and buffers */
#define UD_TRB_NRX      0x1060          /* ep3 OUT (bulk) */
#define UD_TRB_NTX      0x1070          /* ep3 IN (bulk) */
#define UD_TRB_NINT     0x1080          /* ep4 IN (interrupt) */
#define UD_NNOTIFY      0x1320          /* 8-byte RESPONSE_AVAILABLE */
#define UD_NRX          0x3000
#define UD_NTX          0x3800
''')
edit('''#define EP_INT          5               /* 0x82 interrupt IN */
''', '''#define EP_INT          5               /* 0x82 interrupt IN */
#define EP_NRX          6               /* 0x03 bulk OUT (RNDIS) */
#define EP_NTX          7               /* 0x83 bulk IN (RNDIS) */
#define EP_NINT         9               /* 0x84 interrupt IN (RNDIS) */
''')
edit('''	bool        serial, serial_dtr, serial_line_out;
''', '''	bool        serial, serial_dtr, serial_line_out;
	bool        net, rndis;     /* a network function (ECM, or RNDIS beside the console) */
	unsigned    ep_nrx, ep_ntx, ep_nint;
	uint32_t    trb_nrx, trb_ntx, trb_nint, buf_nrx, buf_ntx, buf_nnotify;
	uint32_t    net_addr;       /* ue0's IPv4 address; the host is .1 of the same /24 */
	bool        net_tx_busy;
	bool        rndis_cmd_out;
	uint32_t    ep0_out_len;
	uint32_t    rndis_filter;   /* OID_GEN_CURRENT_PACKET_FILTER: 0 = no data yet */
	uint8_t     rndis_resp[512];
	uint32_t    rndis_resp_len;
	uint64_t    rx_dropped;
''')
edit('''_Static_assert(sizeof(ud_serial_cfg_desc) == 67, "ACM configuration length");
''', '''_Static_assert(sizeof(ud_serial_cfg_desc) == 67, "ACM configuration length");
/* sweetusb=4: console (ACM, interfaces 0/1) and RNDIS (interfaces 2/3), each behind an IAD. */
static const uint8_t ud_combo_dev_desc[18] = {
	18, 1, 0x00, 0x02, 0xef, 0x02, 0x01, 64,
	0x09, 0x12, 0x03, 0x00, 0x00, 0x01, 1, 2, 3, 1,
};
static const uint8_t ud_combo_cfg_desc[] = {
	9, 2, 141, 0, 4, 1, 0, 0x80, 250,
	8, 0x0b, 0, 2, 0x02, 0x02, 0x01, 0,       /* IAD: ACM console */
	9, 4, 0, 0, 1, 0x02, 0x02, 0x01, 0,
	5, 0x24, 0x00, 0x10, 0x01,
	5, 0x24, 0x01, 0, 1,
	4, 0x24, 0x02, 2,
	5, 0x24, 0x06, 0, 1,
	7, 5, 0x82, 0x03, 16, 0, 9,
	9, 4, 1, 0, 2, 0x0a, 0, 0, 0,
	7, 5, 0x81, 0x02, 0x00, 0x02, 0,
	7, 5, 0x01, 0x02, 0x00, 0x02, 0,
	8, 0x0b, 2, 2, 0xe0, 0x01, 0x03, 0,       /* IAD: RNDIS (wireless controller / RNDIS) */
	9, 4, 2, 0, 1, 0xe0, 0x01, 0x03, 0,
	5, 0x24, 0x00, 0x10, 0x01,
	5, 0x24, 0x01, 0, 3,
	4, 0x24, 0x02, 0,
	5, 0x24, 0x06, 2, 3,
	7, 5, 0x84, 0x03, 8, 0, 9,
	9, 4, 3, 0, 2, 0x0a, 0, 0, 0,
	7, 5, 0x83, 0x02, 0x00, 0x02, 0,
	7, 5, 0x03, 0x02, 0x00, 0x02, 0,
};
_Static_assert(sizeof(ud_combo_cfg_desc) == 141, "console + RNDIS configuration length");
''')
edit('''	const char *str = ud.serial && idx == 2 ? "Sweet iOS (USB console)" : ud_strings[idx];
''', '''	const char *str = ud.rndis && idx == 2 ? "Sweet iOS (USB console + network)" :
	    ud.serial && idx == 2 ? "Sweet iOS (USB console)" : ud_strings[idx];
''')
edit('''static void ud_rx_arm(void);
static void ud_tx_kick_locked(void);
static void ud_link_event(bool up);
''', r'''static void ud_rx_arm(void);
static void ud_serial_rx_arm(void);
static void ud_tx_kick_locked(void);
static void ud_link_event(bool up);

/* ---- RNDIS control (sweetusb=4) ---- */

#define RNDIS_PACKET            1
#define RNDIS_INIT              2
#define RNDIS_HALT              3
#define RNDIS_QUERY             4
#define RNDIS_SET               5
#define RNDIS_RESET             6
#define RNDIS_KEEPALIVE         8
#define RNDIS_CMPLT             0x80000000u
#define RNDIS_SUCCESS           0u
#define RNDIS_NOT_SUPPORTED     0xc00000bbu
#define RNDIS_INVALID_DATA      0xc0010015u
#define RNDIS_HEADER            44u
#define RNDIS_MAX_TRANSFER      1600u

static void
rndis_put32(uint8_t *p, uint32_t v)
{
	p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24);
}

static uint32_t
rndis_get32(const uint8_t *p)
{
	return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

/* The host side's MAC: RNDIS reports it as the adapter's own (OID_802_3_*_ADDRESS). */
static const uint8_t ud_host_mac[ETHER_ADDR_LEN] = { 0x02, 0x00, 0x5e, 0x77, 0xee, 0x01 };

/* Answer to an OID query in out; its length, or ~0u if the OID is not supported. */
static uint32_t
rndis_query(uint32_t oid, uint8_t *out)
{
	static const uint32_t supported[] = {
		0x00010101, 0x00010102, 0x00010103, 0x00010104, 0x00010106, 0x00010107, 0x0001010a,
		0x0001010b, 0x0001010c, 0x0001010d, 0x0001010e, 0x00010111, 0x00010114, 0x00010202,
		0x00020101, 0x00020102, 0x00020103, 0x00020104, 0x00020105,
		0x01010101, 0x01010102, 0x01010103, 0x01010104,
		0x01020101, 0x01020102, 0x01020103,
	};
	uint32_t value;

	switch (oid) {
	case 0x00010101:        /* OID_GEN_SUPPORTED_LIST */
		for (unsigned i = 0; i < sizeof(supported) / sizeof(supported[0]); i++) {
			rndis_put32(out + 4 * i, supported[i]);
		}
		return sizeof(supported);
	case 0x0001010d: {      /* OID_GEN_VENDOR_DESCRIPTION */
		static const char desc[] = "ios-sweet USB network";
		memcpy(out, desc, sizeof(desc));
		return sizeof(desc);
	}
	case 0x01010101:        /* OID_802_3_PERMANENT_ADDRESS */
	case 0x01010102:        /* OID_802_3_CURRENT_ADDRESS */
		memcpy(out, ud_host_mac, ETHER_ADDR_LEN);
		return ETHER_ADDR_LEN;
	case 0x00010102: value = 0; break;                      /* hardware status: ready */
	case 0x00010103: case 0x00010104: value = 0; break;     /* medium: 802.3 */
	case 0x00010106: value = ETHERMTU; break;               /* maximum frame size */
	case 0x00010107: value = 4800000; break;                /* link speed, 100 bps units: 480 Mbit/s */
	case 0x0001010a: case 0x0001010b: value = ETHER_MAX_LEN - ETHER_CRC_LEN; break;
	case 0x0001010c: value = 0x00ffffff; break;             /* vendor ID: none */
	case 0x0001010e: value = ud.rndis_filter; break;
	case 0x00010111: value = RNDIS_HEADER + ETHER_MAX_LEN - ETHER_CRC_LEN; break;
	case 0x00010114: value = 0; break;                      /* media connect status: connected */
	case 0x00010202: value = 0; break;                      /* physical medium: unspecified */
	case 0x00020101: value = (uint32_t)ud.tx_frames; break;
	case 0x00020102: value = (uint32_t)ud.rx_frames; break;
	case 0x00020103: case 0x00020104: value = 0; break;
	case 0x00020105: value = (uint32_t)ud.rx_dropped; break;
	case 0x01010103: value = 0xe0000000u; break;            /* multicast list: the base only */
	case 0x01010104: value = 32; break;                     /* maximum multicast list size */
	case 0x01020101: case 0x01020102: case 0x01020103: value = 0; break;
	default:
		return ~0u;
	}
	rndis_put32(out, value);
	return 4;
}

/* RESPONSE_AVAILABLE on the RNDIS interrupt endpoint: the host then asks for it on endpoint 0. */
static void
rndis_notify(void)
{
	uint8_t *n = (uint8_t *)(ud.dma + ud.buf_nnotify);
	memset(n, 0, 8);
	n[0] = 1;
	ud_start_trb(ud.ep_nint, ud.trb_nint, ud.buf_nnotify, 8, TRBCTL_NORMAL);
}

/* One encapsulated command (len bytes at msg): its completion goes to ud.rndis_resp. */
static void
rndis_command(const uint8_t *msg, uint32_t len)
{
	uint8_t *r = ud.rndis_resp;
	uint32_t type = len >= 8 ? rndis_get32(msg) : 0;
	uint32_t id = len >= 12 ? rndis_get32(msg + 8) : 0;
	static unsigned logged;

	if (logged++ < 24) {
		printf("SWEET USB: RNDIS message %u (%u bytes)\n", type, len);
	}
	memset(r, 0, 64);
	switch (type) {
	case RNDIS_INIT:
		rndis_put32(r, RNDIS_INIT | RNDIS_CMPLT);
		rndis_put32(r + 4, 52);
		rndis_put32(r + 8, id);
		rndis_put32(r + 12, RNDIS_SUCCESS);
		rndis_put32(r + 16, 1);                 /* version 1.0 */
		rndis_put32(r + 24, 1);                 /* connectionless */
		rndis_put32(r + 28, 0);                 /* 802.3 */
		rndis_put32(r + 32, 1);                 /* one packet a transfer */
		rndis_put32(r + 36, RNDIS_MAX_TRANSFER);
		ud.rndis_resp_len = 52;
		break;
	case RNDIS_QUERY: {
		uint32_t oid = len >= 16 ? rndis_get32(msg + 12) : 0;
		uint32_t n = rndis_query(oid, r + 24);
		bool ok = n != ~0u;
		rndis_put32(r, RNDIS_QUERY | RNDIS_CMPLT);
		rndis_put32(r + 4, 24 + (ok ? n : 0));
		rndis_put32(r + 8, id);
		rndis_put32(r + 12, ok ? RNDIS_SUCCESS : RNDIS_NOT_SUPPORTED);
		rndis_put32(r + 16, ok ? n : 0);
		rndis_put32(r + 20, ok && n ? 16 : 0);
		ud.rndis_resp_len = 24 + (ok ? n : 0);
		if (!ok && logged < 48) {
			printf("SWEET USB: RNDIS query of OID 0x%08x not supported\n", oid);
		}
		break;
	}
	case RNDIS_SET: {
		uint32_t oid = len >= 16 ? rndis_get32(msg + 12) : 0;
		uint32_t blen = len >= 20 ? rndis_get32(msg + 16) : 0;
		uint32_t boff = len >= 24 ? rndis_get32(msg + 20) + 8 : 0;
		uint32_t status = RNDIS_SUCCESS;
		if (oid == 0x0001010e) {                /* OID_GEN_CURRENT_PACKET_FILTER */
			if (blen >= 4 && boff <= len && blen <= len - boff) {
				bool was = ud.rndis_filter != 0;
				ud.rndis_filter = rndis_get32(msg + boff);
				printf("SWEET USB: RNDIS packet filter 0x%x\n", ud.rndis_filter);
				if (!was && ud.rndis_filter) {
					ud_link_event(true);
				}
			} else {
				status = RNDIS_INVALID_DATA;
			}
		} else if (oid != 0x01010103 && oid != 0x00010116) {    /* multicast list, driver version */
			status = RNDIS_NOT_SUPPORTED;
		}
		rndis_put32(r, RNDIS_SET | RNDIS_CMPLT);
		rndis_put32(r + 4, 16);
		rndis_put32(r + 8, id);
		rndis_put32(r + 12, status);
		ud.rndis_resp_len = 16;
		break;
	}
	case RNDIS_RESET:
		rndis_put32(r, RNDIS_RESET | RNDIS_CMPLT);
		rndis_put32(r + 4, 16);
		rndis_put32(r + 8, RNDIS_SUCCESS);
		rndis_put32(r + 12, 1);                 /* addressing reset */
		ud.rndis_filter = 0;
		ud.rndis_resp_len = 16;
		break;
	case RNDIS_KEEPALIVE:
		rndis_put32(r, RNDIS_KEEPALIVE | RNDIS_CMPLT);
		rndis_put32(r + 4, 16);
		rndis_put32(r + 8, id);
		rndis_put32(r + 12, RNDIS_SUCCESS);
		ud.rndis_resp_len = 16;
		break;
	case RNDIS_HALT:
		ud.rndis_filter = 0;
		return;                                 /* no completion */
	default:
		return;
	}
	rndis_notify();
}
''')
edit('''	if (ud_epcmd(0, DEPCMD_DEPSTARTCFG | (2u << 16), 0, 0, 0) ||
	    ud_epcmd(EP_RX, DEPCMD_SETEPCONFIG, (2u << 1) | (512u << 3), (1u << 8) | ((uint32_t)EP_RX << 25), 0) ||
	    ud_epcmd(EP_RX, DEPCMD_SETTRANSFRESOURCE, 1, 0, 0) ||
	    ud_epcmd(EP_TX, DEPCMD_SETEPCONFIG, (2u << 1) | (512u << 3) | (1u << 17), (1u << 8) | ((uint32_t)EP_TX << 25), 0) ||
	    ud_epcmd(EP_TX, DEPCMD_SETTRANSFRESOURCE, 1, 0, 0) ||
	    ud_epcmd(EP_INT, DEPCMD_SETEPCONFIG, (3u << 1) | (16u << 3) | (2u << 17),
	    (1u << 8) | (8u << 16) | ((uint32_t)EP_INT << 25), 0) ||
	    ud_epcmd(EP_INT, DEPCMD_SETTRANSFRESOURCE, 1, 0, 0)) {
		printf("SWEET USB: data endpoints setup failed\\n");
		return;
	}
	dwc_wr(DALEPENA, dwc_rd(DALEPENA) | (1u << EP_RX) | (1u << EP_TX) | (1u << EP_INT));
	ud.configured = true;
	ud_rx_arm();
	printf("SWEET USB: %s endpoints configured\\n", ud.serial ? "ACM" : "ECM");
''', '''	if (ud_epcmd(0, DEPCMD_DEPSTARTCFG | (2u << 16), 0, 0, 0) ||
	    ud_epcmd(EP_RX, DEPCMD_SETEPCONFIG, (2u << 1) | (512u << 3), (1u << 8) | ((uint32_t)EP_RX << 25), 0) ||
	    ud_epcmd(EP_RX, DEPCMD_SETTRANSFRESOURCE, 1, 0, 0) ||
	    ud_epcmd(EP_TX, DEPCMD_SETEPCONFIG, (2u << 1) | (512u << 3) | (1u << 17), (1u << 8) | ((uint32_t)EP_TX << 25), 0) ||
	    ud_epcmd(EP_TX, DEPCMD_SETTRANSFRESOURCE, 1, 0, 0) ||
	    ud_epcmd(EP_INT, DEPCMD_SETEPCONFIG, (3u << 1) | (16u << 3) | (2u << 17),
	    (1u << 8) | (8u << 16) | ((uint32_t)EP_INT << 25), 0) ||
	    ud_epcmd(EP_INT, DEPCMD_SETTRANSFRESOURCE, 1, 0, 0)) {
		printf("SWEET USB: data endpoints setup failed\\n");
		return;
	}
	/* The RNDIS function: bulk 0x03/0x83 (TX FIFO 3), interrupt 0x84 (TX FIFO 4). */
	if (ud.rndis &&
	    (ud_epcmd(EP_NRX, DEPCMD_SETEPCONFIG, (2u << 1) | (512u << 3), (1u << 8) | ((uint32_t)EP_NRX << 25), 0) ||
	    ud_epcmd(EP_NRX, DEPCMD_SETTRANSFRESOURCE, 1, 0, 0) ||
	    ud_epcmd(EP_NTX, DEPCMD_SETEPCONFIG, (2u << 1) | (512u << 3) | (3u << 17), (1u << 8) | ((uint32_t)EP_NTX << 25), 0) ||
	    ud_epcmd(EP_NTX, DEPCMD_SETTRANSFRESOURCE, 1, 0, 0) ||
	    ud_epcmd(EP_NINT, DEPCMD_SETEPCONFIG, (3u << 1) | (8u << 3) | (4u << 17),
	    (1u << 8) | (8u << 16) | ((uint32_t)EP_NINT << 25), 0) ||
	    ud_epcmd(EP_NINT, DEPCMD_SETTRANSFRESOURCE, 1, 0, 0))) {
		printf("SWEET USB: RNDIS endpoints setup failed\\n");
		return;
	}
	dwc_wr(DALEPENA, dwc_rd(DALEPENA) | (1u << EP_RX) | (1u << EP_TX) | (1u << EP_INT) |
	    (ud.rndis ? (1u << EP_NRX) | (1u << EP_NTX) | (1u << EP_NINT) : 0));
	ud.configured = true;
	if (ud.serial) {
		ud_serial_rx_arm();
	}
	if (ud.net) {
		ud_rx_arm();
	}
	printf("SWEET USB: %s endpoints configured\\n", ud.rndis ? "ACM + RNDIS" : ud.serial ? "ACM" : "ECM");
''')
edit('''	ud.data_in = (type & 0x80) != 0;
	ud.serial_line_out = false;
	if (ud.serial && (type & 0x60) == 0x20) {
''', '''	ud.data_in = (type & 0x80) != 0;
	ud.serial_line_out = false;
	ud.rndis_cmd_out = false;
	if (ud.rndis && (type & 0x60) == 0x20 && (index & 0xff) == 2) {
		if (type == 0x21 && req == 0x00 && length > 0 && length <= 512) {
			ud.rndis_cmd_out = true;        /* SEND_ENCAPSULATED_COMMAND */
			ud.ep0_out_len = length;
		} else if (type == 0xa1 && req == 0x01) {       /* GET_ENCAPSULATED_RESPONSE */
			if (ud.rndis_resp_len) {
				n = ud.rndis_resp_len;
				memcpy(data, ud.rndis_resp, n);
				ud.rndis_resp_len = 0;
			} else {
				data[0] = 0;
				n = 1;
			}
		} else {
			ok = false;
		}
	} else if (ud.serial && (type & 0x60) == 0x20) {
''')
edit('''			case 1:
			n = sizeof(ud_dev_desc);
			memcpy(data, ud.serial ? ud_serial_dev_desc : ud_dev_desc, n);
			break;
		case 2:
			n = ud.serial ? sizeof(ud_serial_cfg_desc) : sizeof(ud_cfg_desc);
			memcpy(data, ud.serial ? ud_serial_cfg_desc : ud_cfg_desc, n);
			break;
''' if False else '''		case 1:
			n = sizeof(ud_dev_desc);
			memcpy(data, ud.serial ? ud_serial_dev_desc : ud_dev_desc, n);
			break;
		case 2:
			n = ud.serial ? sizeof(ud_serial_cfg_desc) : sizeof(ud_cfg_desc);
			memcpy(data, ud.serial ? ud_serial_cfg_desc : ud_cfg_desc, n);
			break;
''', '''		case 1:
			n = sizeof(ud_dev_desc);
			memcpy(data, ud.rndis ? ud_combo_dev_desc : ud.serial ? ud_serial_dev_desc : ud_dev_desc, n);
			break;
		case 2:
			n = ud.rndis ? sizeof(ud_combo_cfg_desc) : ud.serial ? sizeof(ud_serial_cfg_desc) : sizeof(ud_cfg_desc);
			memcpy(data, ud.rndis ? ud_combo_cfg_desc : ud.serial ? ud_serial_cfg_desc : ud_cfg_desc, n);
			break;
''')
edit('''		if (!ud.serial && index == 1) {
''', '''		if (ud.net && !ud.rndis && index == 1) {
''')
edit('''		/* DWC3 control OUT TRBs cover one whole EP0 packet, including
		 * the seven-byte ACM SET_LINE_CODING payload. */
		ud_start(0, UD_DATA, 64, TRBCTL_DATA);
''', '''		/* DWC3 control OUT TRBs cover whole EP0 packets: the seven-byte ACM
		 * SET_LINE_CODING payload, or an RNDIS message of up to 512 bytes. */
		ud_start(0, UD_DATA, (length + 63u) & ~63u, TRBCTL_DATA);
''')
# the data path: the network endpoints and buffers are per mode
edit('''static void
ud_rx_arm(void)
{
	ud_start_trb(EP_RX, UD_TRB_RX, UD_RX, UD_FRAME_MAX, TRBCTL_NORMAL);
}

static void
ud_rx_done(void)
{
	volatile uint32_t *t = (volatile uint32_t *)(ud.dma + UD_TRB_RX);
	ud_sync(UD_TRB_RX, 16);
	uint32_t len = UD_FRAME_MAX - (t[2] & 0xffffff);
	ud_sync(UD_RX, UD_FRAME_MAX);
	if (ud.ifp != NULL && len >= ETHER_HDR_LEN && len <= ETHER_MAX_LEN) {
''', '''static void
ud_rx_arm(void)
{
	ud_start_trb(ud.ep_nrx, ud.trb_nrx, ud.buf_nrx, UD_FRAME_MAX, TRBCTL_NORMAL);
}

/* The console's OUT endpoint: anything the host sends is ignored. */
static void
ud_serial_rx_arm(void)
{
	ud_start_trb(EP_RX, UD_TRB_RX, UD_RX, UD_FRAME_MAX, TRBCTL_NORMAL);
}

static void
ud_rx_done(void)
{
	volatile uint32_t *t = (volatile uint32_t *)(ud.dma + ud.trb_nrx);
	ud_sync(ud.trb_nrx, 16);
	uint32_t len = UD_FRAME_MAX - (t[2] & 0xffffff);
	ud_sync(ud.buf_nrx, UD_FRAME_MAX);
	const uint8_t *frame = (const uint8_t *)(ud.dma + ud.buf_nrx);
	if (ud.rndis) {
		/* One RNDIS_PACKET_MSG a transfer (INIT_CMPLT said so): the frame is DataOffset after +8. */
		uint32_t off = len >= RNDIS_HEADER ? rndis_get32(frame + 8) + 8 : 0;
		uint32_t dlen = len >= RNDIS_HEADER ? rndis_get32(frame + 12) : 0;
		if (len < RNDIS_HEADER || rndis_get32(frame) != RNDIS_PACKET || off < 8 || off > len || dlen > len - off) {
			ud.rx_dropped++;
			len = 0;
		} else {
			frame += off;
			len = dlen;
		}
	}
	if (ud.ifp != NULL && len >= ETHER_HDR_LEN && len <= ETHER_MAX_LEN) {
''')
edit('''			memcpy(mbuf_data(m), (const void *)(ud.dma + UD_RX), len);
''', '''			memcpy(mbuf_data(m), frame, len);
''')
edit('''	while (!ud.tx_busy && ud.txq_count > 0 && ud.configured) {
		mbuf_t m = ud.txq[ud.txq_head];
		ud.txq_head = (ud.txq_head + 1) % UD_TXQ;
		ud.txq_count--;
		size_t len = mbuf_pkthdr_len(m);
		if (len > ETHER_MAX_LEN - ETHER_CRC_LEN) {
			mbuf_freem(m);
			continue;
		}
		mbuf_copydata(m, 0, len, (void *)(ud.dma + UD_TX));
		mbuf_freem(m);
		/* A frame of a multiple of 512 bytes would need a zero-length
		 * packet to end it; one pad byte does the same (IP ignores it). */
		if ((len % 512) == 0) {
			((uint8_t *)(ud.dma + UD_TX))[len++] = 0;
		}
		ud.tx_busy = true;
		ud.tx_frames++;
		ud_start_trb(EP_TX, UD_TRB_TX, UD_TX, (uint32_t)len, TRBCTL_NORMAL);
	}
''', '''	while (!ud.net_tx_busy && ud.txq_count > 0 && ud.configured) {
		mbuf_t m = ud.txq[ud.txq_head];
		ud.txq_head = (ud.txq_head + 1) % UD_TXQ;
		ud.txq_count--;
		size_t len = mbuf_pkthdr_len(m);
		if (len > ETHER_MAX_LEN - ETHER_CRC_LEN) {
			mbuf_freem(m);
			continue;
		}
		uint8_t *out = (uint8_t *)(ud.dma + ud.buf_ntx);
		size_t head = ud.rndis ? RNDIS_HEADER : 0;
		if (ud.rndis) {
			memset(out, 0, RNDIS_HEADER);
			rndis_put32(out, RNDIS_PACKET);
			rndis_put32(out + 4, (uint32_t)(RNDIS_HEADER + len));
			rndis_put32(out + 8, RNDIS_HEADER - 8);         /* DataOffset, from +8 */
			rndis_put32(out + 12, (uint32_t)len);
		}
		mbuf_copydata(m, 0, len, out + head);
		mbuf_freem(m);
		len += head;
		/* A transfer of a multiple of 512 bytes would need a zero-length
		 * packet to end it; one pad byte does the same (IP and Windows'
		 * RNDIS driver ignore it, as with Linux's gadget). */
		if ((len % 512) == 0) {
			out[len++] = 0;
		}
		ud.net_tx_busy = true;
		ud.tx_frames++;
		ud_start_trb(ud.ep_ntx, ud.trb_ntx, ud.buf_ntx, (uint32_t)len, TRBCTL_NORMAL);
	}
''')
edit('''	lck_mtx_lock(ud.lock);
	if (ud.txq_count == UD_TXQ || !ud.configured) {
''', '''	lck_mtx_lock(ud.lock);
	if (ud.txq_count == UD_TXQ || !ud.configured || (ud.rndis && ud.rndis_filter == 0)) {
''')
edit('''/* ue0, 192.168.7.2/24 (the host side is 192.168.7.1). */
''', '''/* ue0, 192.168.7.2/24 (the host side is 192.168.7.1); with RNDIS 192.168.137.2/24, beside the
 * PC's Internet Connection Sharing at 192.168.137.1. */
''')
edit('''		a->sin_addr.s_addr = htonl(0xc0a80702);         /* 192.168.7.2 */
''', '''		a->sin_addr.s_addr = htonl(ud.net_addr);
''')
edit('''		a->sin_addr.s_addr = htonl(0xc0a807ff);
		err = sock_ioctl(so, SIOCAIFADDR, &ifra);
		sock_close(so);
	}
	ifnet_set_flags(ud.ifp, IFF_UP | IFF_RUNNING, IFF_UP | IFF_RUNNING);
	printf("SWEET USB: ue0 192.168.7.2/24 %s (err %d)\\n", err ? "NOT configured" : "up", err);
''', '''		a->sin_addr.s_addr = htonl((ud.net_addr & 0xffffff00u) | 0xff);
		err = sock_ioctl(so, SIOCAIFADDR, &ifra);
		sock_close(so);
	}
	ifnet_set_flags(ud.ifp, IFF_UP | IFF_RUNNING, IFF_UP | IFF_RUNNING);
	printf("SWEET USB: ue0 %u.%u.%u.%u/24 %s (err %d)\\n", ud.net_addr >> 24, (ud.net_addr >> 16) & 0xff,
	    (ud.net_addr >> 8) & 0xff, ud.net_addr & 0xff, err ? "NOT configured" : "up", err);
''')
edit('''	if (ep == EP_RX && type == 1) {
		if (ud.serial) {
			ud_rx_arm(); /* console output only */
			return;
		}
		ud_rx_done();
		return;
	}
	if (ep == EP_TX && type == 1) {
		if (ud.serial) {
			ud.tx_busy = false;
			return;
		}
		lck_mtx_lock(ud.lock);
		ud.tx_busy = false;
		ud_tx_kick_locked();
		lck_mtx_unlock(ud.lock);
		return;
	}
''', '''	if (ud.net && ep == ud.ep_nrx && type == 1) {
		ud_rx_done();
		return;
	}
	if (ud.net && ep == ud.ep_ntx && type == 1) {
		lck_mtx_lock(ud.lock);
		ud.net_tx_busy = false;
		ud_tx_kick_locked();
		lck_mtx_unlock(ud.lock);
		return;
	}
	if (ud.serial && ep == EP_RX && type == 1) {
		ud_serial_rx_arm(); /* console output only */
		return;
	}
	if (ud.serial && ep == EP_TX && type == 1) {
		ud.tx_busy = false;
		return;
	}
''')
edit('''			if (ud.serial_line_out) {
''', '''			if (ud.rndis_cmd_out) {
				ud_sync(UD_DATA, ud.ep0_out_len);
				rndis_command((const uint8_t *)(ud.dma + UD_DATA), ud.ep0_out_len);
				ud.rndis_cmd_out = false;
			}
			if (ud.serial_line_out) {
''')
edit('''		if (ud.serial) {
			ud_serial_tx();
		} else if ((++ticks % 30000) == 0) {
			printf("SWEET USB: ue0 rx %llu tx %llu frames\\n", ud.rx_frames, ud.tx_frames);
		}
''', '''		if (ud.serial) {
			ud_serial_tx();
		}
		if (ud.net && (++ticks % 30000) == 0) {
			printf("SWEET USB: ue0 rx %llu tx %llu frames, %llu dropped\\n", ud.rx_frames, ud.tx_frames, ud.rx_dropped);
		}
''')
edit('''	to.sin_addr.s_addr = htonl(0xc0a80701);         /* 192.168.7.1 */
''', '''	to.sin_addr.s_addr = htonl((ud.net_addr & 0xffffff00u) | 1);   /* the host */
''')
edit('''static void
sweet_usb_gadget_start(vm_offset_t dwc, bool serial)
{
''', '''static void
sweet_usb_gadget_start(vm_offset_t dwc, int mode)
{
	bool serial = mode == 3 || mode == 4;
''')
edit('''	ud.dma_pa = ptoa_64(pn);
	ud.serial = serial;
	if (serial) {
		const uint8_t line[] = {0x00, 0xc2, 0x01, 0x00, 0, 0, 8}; /* 115200 8N1 */
		memcpy(ud.serial_line, line, sizeof(line));
	} else {
		ud_if_create();
	}
''', '''	ud.dma_pa = ptoa_64(pn);
	ud.serial = serial;
	ud.net = mode == 2 || mode == 4;
	ud.rndis = mode == 4;
	if (ud.rndis) {
		ud.ep_nrx = EP_NRX; ud.ep_ntx = EP_NTX; ud.ep_nint = EP_NINT;
		ud.trb_nrx = UD_TRB_NRX; ud.trb_ntx = UD_TRB_NTX; ud.trb_nint = UD_TRB_NINT;
		ud.buf_nrx = UD_NRX; ud.buf_ntx = UD_NTX; ud.buf_nnotify = UD_NNOTIFY;
		ud.net_addr = 0xc0a88902;               /* 192.168.137.2 */
	} else {
		ud.ep_nrx = EP_RX; ud.ep_ntx = EP_TX; ud.ep_nint = EP_INT;
		ud.trb_nrx = UD_TRB_RX; ud.trb_ntx = UD_TRB_TX; ud.trb_nint = UD_TRB_INT;
		ud.buf_nrx = UD_RX; ud.buf_ntx = UD_TX; ud.buf_nnotify = UD_NOTIFY;
		ud.net_addr = 0xc0a80702;               /* 192.168.7.2 */
	}
	if (serial) {
		const uint8_t line[] = {0x00, 0xc2, 0x01, 0x00, 0, 0, 8}; /* 115200 8N1 */
		memcpy(ud.serial_line, line, sizeof(line));
	}
	if (ud.net) {
		ud_if_create();
	}
	printf("SWEET USB: TX FIFOs 0x%08x 0x%08x 0x%08x 0x%08x 0x%08x\\n", dwc_rd(0xc300), dwc_rd(0xc304),
	    dwc_rd(0xc308), dwc_rd(0xc30c), dwc_rd(0xc310));
''')
edit('''	if (livelog && ud.ifp != NULL && kernel_thread_start(ud_log_thread, NULL, &thread) == KERN_SUCCESS) {
''', '''	/* (with the console beside it, the console carries the log) */
	if (livelog && ud.ifp != NULL && !ud.serial && kernel_thread_start(ud_log_thread, NULL, &thread) == KERN_SUCCESS) {
''')

assert 'ud.tx_busy = true;\n\t\tud.tx_frames++;' not in new

with tempfile.TemporaryDirectory(prefix='make-0211-', dir='D:/ios-sweet/build') as scratch:
    work = Path(scratch)
    for side, data in (('a', base), ('b', new)):
        path = work / side / USB
        path.parent.mkdir(parents=True)
        path.write_bytes(data.encode())
    done = subprocess.run(GIT + ['diff', '--no-index', '--no-color', '--no-prefix', '-U3', 'a', 'b'], cwd=work, capture_output=True)
    assert done.returncode == 1, done.stderr
    text = re.sub(r'^diff --git .*\n(index .*\n)?', '', done.stdout.decode(), flags=re.M)
    assert text.startswith('--- a/') and '\r' not in text
    output = REPO / 'xnu/patches' / NAME
    output.write_bytes(text.encode())
    check = work / 'check' / USB
    check.parent.mkdir(parents=True)
    check.write_bytes(base.encode())
    subprocess.run(GIT + ['apply', str(output)], cwd=work / 'check', check=True)
    assert check.read_bytes() == new.encode()
    subprocess.run(GIT + ['apply', '--reverse', str(output)], cwd=work / 'check', check=True)
(TREE / 'bsd/dev/sweet_usb.base0211.c').write_bytes(base.encode())
(TREE / 'bsd/dev/sweet_usb.new0211.c').write_bytes(new.encode())
print(NAME, len(text.splitlines()), 'lines, forward and reverse verified')

script = REPO / 'tools/check-sweet-patch-reversal.sh'
lines = script.read_bytes().decode().replace('\r\n', '\n').split('\n')
assert not any(NAME in line for line in lines)
at = [i for i, line in enumerate(lines) if '0180-sweet-usb-console-and-b3a8-evidence.patch' in line and 'apply --reverse' in line]
for i in at:
    if '--exclude=' + USB not in lines[i]:
        lines[i] = lines[i].replace(' --check ', ' --check --exclude=' + USB + ' ', 1)
print('0180 lines adjusted:', len(at))
last = max(i for i, line in enumerate(lines) if 'apply --reverse --check' in line or 'grep -F' in line)
lines.insert(last + 1, '# 0211: sweetusb=4, the USB console beside an RNDIS network function.')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())
print('reversal script updated')
