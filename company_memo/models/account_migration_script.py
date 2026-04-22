#!/usr/bin/env python3
import odoorpc
import ssl
import time
import uuid

# ============================================================
# CONFIG
# ============================================================
SRC = {
    "host": "137.184.118.183",
    "port": 8069,
    "db": "live_new",
    "user": "roooot",
    "password": "xxxxxx",
}

DEST = {
    "host": "178.62.23.202",
    "port": 8069,
    "db": "bilead",
    "user": "roooot",
    "password": "xxxxxx",
}

XML_MODULE = "__export__"     # use __export__ as requested


# ============================================================
# SSL FIX (if needed)
# ============================================================
ssl._create_default_https_context = ssl._create_unverified_context


# ============================================================
# CONNECT
# ============================================================
def connect(info):
    o = odoorpc.ODOO(info["host"], port=info["port"])
    o.login(info["db"], info["user"], info["password"])
    print(f"[CONNECTED] {info['host']} / {info['db']}")
    return o


src = connect(SRC)
dest = connect(DEST)


# ============================================================
# XML ID UTILITIES
# ============================================================
def get_source_xml_id(model, res_id):
    """Return xml_id string or None."""
    mdl = src.env["ir.model.data"]
    rec = mdl.search([("model", "=", model), ("res_id", "=", res_id)], limit=1)
    if not rec:
        return None
    r = mdl.browse(rec)
    return f"{r.module}.{r.name}"


def get_dest_record_by_xml(xmlid):
    """Return target record id or None."""
    if not xmlid or "." not in xmlid:
        return None

    module, name = xmlid.split(".")

    # check if xmlid exists
    mdl = dest.env["ir.model.data"]
    rec = mdl.search([("module", "=", module), ("name", "=", name)], limit=1)
    if not rec:
        return None

    return mdl.browse(rec).res_id


def create_dest_xml_id(model, res_id, xmlid):
    """Create XML ID in destination DB."""
    module, name = xmlid.split(".")

    dest.env["ir.model.data"].create({
        "module": module,
        "name": name,
        "model": model,
        "res_id": res_id,
        "noupdate": True,
    })


def generate_export_xmlid(model_name):
    """Generate Odoo-export style XML ID."""
    return f"{XML_MODULE}.{model_name}_{uuid.uuid4().hex[:8]}"


# ============================================================
# RELATIONAL MAPPER
# ============================================================
def map_record(model, src_id):
    """
    1. Try get source XML ID.
    2. Try find target record with same XML ID.
    3. If not found → create record in target + create xml id.
    """
    if not src_id:
        return False

    src_rec = src.env[model].browse(src_id)

    # --- STEP 1: get source xmlid ---
    xmlid = get_source_xml_id(model, src_id)

    # if source missing xml id → create temporary one in source logic
    if not xmlid:
        xmlid = generate_export_xmlid(model.replace(".", "_"))

    # --- STEP 2: check target ---
    dest_id = get_dest_record_by_xml(xmlid)
    if dest_id:
        return dest_id

    # --- STEP 3: auto-create record in target ---
    vals = {}
    for f in src_rec._fields:
        if f in ("id", "create_uid", "create_date", "write_uid", "write_date"):
            continue

        ftype = src_rec._fields[f].type
        val = getattr(src_rec, f)

        if ftype == "many2one":
            vals[f] = map_record(src_rec._fields[f].comodel_name, val.id) if val else False

        elif ftype in ("char", "text", "date", "datetime", "float", "integer", "monetary", "boolean"):
            vals[f] = val

        elif ftype == "many2many":
            ids = [map_record(src_rec._fields[f].comodel_name, i) for i in val.ids]
            vals[f] = [(6, 0, [i for i in ids if i])]

        else:
            # skip one2many & other unusual fields
            pass

    # create new record
    new_id = dest.env[model].create(vals)

    # create xml id in destination
    create_dest_xml_id(model, new_id, xmlid)

    print(f"[AUTO-CREATED] {model} {src_id} → {new_id} ({xmlid})")

    return new_id


# ============================================================
# MIGRATE ACCOUNT MOVES
# ============================================================
src_move = src.env["account.move"]
dest_move = dest.env["account.move"]

moves = src_move.search([])
print(f"[INFO] Migrating {len(moves)} account moves...\n")

for mid in moves:
    m = src_move.browse(mid)

    # XML ID of the move
    xmlid = get_source_xml_id("account.move", mid)
    if xmlid:
        existing = get_dest_record_by_xml(xmlid)
        if existing:
            print(f"[SKIP] Move already exists: {xmlid}")
            continue
    else:
        xmlid = generate_export_xmlid("account_move")

    # --- MAP RELATIONS ---
    journal = map_record("account.journal", m.journal_id.id)
    partner = map_record("res.partner", m.partner_id.id) if m.partner_id else False
    payment_term = map_record("account.payment.term", m.invoice_payment_term_id.id) if m.invoice_payment_term_id else False

    vals = {
        "move_type": m.move_type,
        "date": m.date,
        "ref": m.ref or "",
        "journal_id": journal,
        "partner_id": partner,
        "invoice_payment_term_id": payment_term,
        "state": m.state,
        
    }

    new_move = dest_move.create(vals)

    # create xmlid in target
    create_dest_xml_id("account.move", new_move, xmlid)

    print(f"[MOVE CREATED] {mid} → {new_move}   ({xmlid})")

    # -----------------------------------------
    # MIGRATE MOVE LINES
    # -----------------------------------------
    for line in m.line_ids:
        line_xmlid = get_source_xml_id("account.move.line", line.id)
        if not line_xmlid:
            line_xmlid = generate_export_xmlid("account_move_line")

        account = map_record("account.account", line.account_id.id)
        partner = map_record("res.partner", line.partner_id.id) if line.partner_id else False

        lv = {
            "move_id": new_move,
            "name": line.name,
            "account_id": account,
            "debit": line.debit,
            "credit": line.credit,
            "partner_id": partner,
            "date": line.date or m.date,
            "journal_id": journal,
            "state": line.state,
        }

        new_line = dest.env["account.move.line"].create(lv)
        create_dest_xml_id("account.move.line", new_line, line_xmlid)

    # POST MOVE
    try:
        if new_move.state == "posted":
            dest_move.browse(new_move).action_post()
    except:
        pass

    time.sleep(0.1)


print("\n--- SYNC COMPLETE ---\n")
