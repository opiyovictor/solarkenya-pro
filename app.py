from __future__ import annotations
import os, sqlite3, json
from datetime import date, datetime, timedelta
from pathlib import Path
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.units import mm

APP_DIR = Path(__file__).parent
DB_PATH = Path(os.environ.get('SOLARKENYA_DB', APP_DIR / 'data' / 'solarkenya.db'))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
OUT_DIR = APP_DIR / 'generated_documents'
OUT_DIR.mkdir(exist_ok=True)
COMPANY_DEFAULT = {'name':'SolarKenya Pro Ltd','address':'P.O. Box 12345-00100, Nairobi, Kenya','phone':'+254 700 123 456','email':'accounts@example.co.ke','pin':'','bank':'','account':'','mpesa_paybill':'','logo_path':''}
DOC_TYPES = ['Quotation','Tax Invoice','Proforma Invoice','Receipt','Delivery Note','Work Order','Installation Checklist','Commissioning Certificate','Warranty Certificate','Service Report','Customer Handover Pack','Purchase Order']

def db():
    con=sqlite3.connect(DB_PATH)
    con.row_factory=sqlite3.Row
    con.execute('''CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT UNIQUE, doc_type TEXT, customer TEXT, customer_email TEXT, customer_phone TEXT, customer_address TEXT, issue_date TEXT, due_date TEXT, status TEXT, currency TEXT, vat_rate REAL, notes TEXT, items_json TEXT, subtotal REAL, tax REAL, total REAL, created_at TEXT)''')
    con.execute('''CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT, phone TEXT, address TEXT, pin TEXT, created_at TEXT)''')
    con.execute('''CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, customer TEXT, site_location TEXT, system_kw REAL DEFAULT 0, budget REAL DEFAULT 0, status TEXT DEFAULT 'Planned', start_date TEXT, target_date TEXT, notes TEXT, created_at TEXT)''')
    con.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, sku TEXT UNIQUE, item_name TEXT NOT NULL, category TEXT, quantity REAL DEFAULT 0, reorder_level REAL DEFAULT 0, unit_cost REAL DEFAULT 0, location TEXT, supplier TEXT, updated_at TEXT)''')
    con.execute('''CREATE TABLE IF NOT EXISTS service_tickets (id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_no TEXT UNIQUE, customer TEXT, site TEXT, issue TEXT, priority TEXT, status TEXT, assigned_to TEXT, due_date TEXT, notes TEXT, created_at TEXT)''')
    con.execute('''CREATE TABLE IF NOT EXISTS company_settings (key TEXT PRIMARY KEY, value TEXT)''')
    con.commit(); return con

def money(v, currency='KES'):
    return f'{currency} {float(v):,.2f}'

def calc(items, vat_rate):
    clean=[]
    for it in items:
        qty=max(0,float(it.get('qty',0))); price=max(0,float(it.get('unit_price',0)))
        clean.append({**it,'qty':qty,'unit_price':price,'amount':round(qty*price,2)})
    subtotal=round(sum(i['amount'] for i in clean),2); tax=round(subtotal*float(vat_rate)/100,2)
    return clean, subtotal, tax, round(subtotal+tax,2)

def next_number(con, doc_type):
    prefix={'Quotation':'QUO','Tax Invoice':'INV','Proforma Invoice':'PRO','Receipt':'RCT','Delivery Note':'DN','Work Order':'WO','Installation Checklist':'IC','Commissioning Certificate':'CC','Warranty Certificate':'WC','Service Report':'SR','Customer Handover Pack':'HP','Purchase Order':'PO'}.get(doc_type,'DOC')
    year=date.today().year
    row=con.execute("SELECT COUNT(*) n FROM documents WHERE number LIKE ?",(f'{prefix}-{year}-%',)).fetchone()
    return f'{prefix}-{year}-{int(row["n"])+1:04d}'

def make_pdf(payload, company):
    number=payload['number']; path=OUT_DIR/f'{number}.pdf'
    doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=16*mm,leftMargin=16*mm,topMargin=14*mm,bottomMargin=16*mm)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Brand',parent=styles['Title'],fontName='Helvetica-Bold',fontSize=18,leading=22,textColor=colors.HexColor('#0c2546'),spaceAfter=2))
    styles.add(ParagraphStyle(name='DocTitle',parent=styles['Heading1'],fontSize=15,textColor=colors.HexColor('#0b5fb3'),spaceBefore=8,spaceAfter=8))
    styles.add(ParagraphStyle(name='Small',parent=styles['BodyText'],fontSize=8,leading=11,textColor=colors.HexColor('#46566b')))
    styles.add(ParagraphStyle(name='Right',parent=styles['BodyText'],alignment=TA_RIGHT,fontSize=9))
    story=[]
    header=[[Paragraph(company['name'],styles['Brand']),Paragraph(f"<b>{payload['doc_type'].upper()}</b><br/>{number}",styles['Right'])],
            [Paragraph(f"{company['address']}<br/>Tel: {company['phone']}<br/>{company['email']}<br/>KRA PIN: {company['pin'] or 'Not configured'}",styles['Small']),Paragraph(f"<b>Issue date:</b> {payload['issue_date']}<br/><b>Due date:</b> {payload['due_date'] or '—'}<br/><b>Status:</b> {payload['status']}<br/><b>Currency:</b> {payload['currency']}",styles['Small'])]]
    ht=Table(header,colWidths=[105*mm,65*mm]); ht.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),1.5,colors.HexColor('#0b5fb3')),('BOTTOMPADDING',(0,0),(-1,0),8),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)])); story += [ht,Spacer(1,10)]
    story.append(Paragraph('CUSTOMER / BILL TO',styles['Heading3']))
    story.append(Paragraph(f"<b>{payload['customer']}</b><br/>{payload['customer_address'] or ''}<br/>{payload['customer_email'] or ''} {(' | '+payload['customer_phone']) if payload['customer_phone'] else ''}",styles['BodyText']))
    story.append(Spacer(1,12))
    rows=[['#','Description','Qty','Unit price','Amount']]
    for idx,it in enumerate(payload['items'],1): rows.append([str(idx),Paragraph(str(it.get('description','')).replace('&','&amp;'),styles['BodyText']),f"{it['qty']:,.2f}".rstrip('0').rstrip('.'),money(it['unit_price'],payload['currency']),money(it['amount'],payload['currency'])])
    tab=Table(rows,colWidths=[10*mm,77*mm,18*mm,32*mm,33*mm],repeatRows=1)
    tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8f1fb')),('TEXTCOLOR',(0,0),(-1,0),colors.HexColor('#0c2546')),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),8),('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#d6dfeb')),('VALIGN',(0,0),(-1,-1),'TOP'),('ALIGN',(2,1),(-1,-1),'RIGHT'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f8fafc')]),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)])); story += [tab,Spacer(1,12)]
    totals=[[f'Subtotal',money(payload['subtotal'],payload['currency'])],[f"VAT ({payload['vat_rate']:.2f}%)",money(payload['tax'],payload['currency'])],[ 'TOTAL',money(payload['total'],payload['currency'])]]
    tt=Table(totals,colWidths=[55*mm,45*mm],hAlign='RIGHT'); tt.setStyle(TableStyle([('ALIGN',(1,0),(1,-1),'RIGHT'),('FONTNAME',(0,-1),(-1,-1),'Helvetica-Bold'),('BACKGROUND',(0,-1),(-1,-1),colors.HexColor('#e8f1fb')),('LINEABOVE',(0,-1),(-1,-1),1,colors.HexColor('#0b5fb3')),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)])); story += [tt,Spacer(1,16)]
    if payload.get('notes'): story += [Paragraph('NOTES / TERMS',styles['Heading3']),Paragraph(payload['notes'].replace('\n','<br/>'),styles['BodyText']),Spacer(1,10)]
    if company.get('bank') or company.get('account') or company.get('mpesa_paybill'):
        pay=[]
        if company.get('bank'): pay.append(f"Bank: {company['bank']}")
        if company.get('account'): pay.append(f"Account: {company['account']}")
        if company.get('mpesa_paybill'): pay.append(f"M-Pesa Paybill/Till: {company['mpesa_paybill']}")
        story += [Paragraph('<b>Payment instructions</b><br/>'+'<br/>'.join(pay),styles['Small']),Spacer(1,12)]
    story.append(Paragraph('Thank you for your business. Please retain this document for your records.',styles['Small']))
    def footer(canvas, doc_):
        canvas.saveState(); canvas.setStrokeColor(colors.HexColor('#d6dfeb')); canvas.line(16*mm,12*mm,194*mm,12*mm); canvas.setFont('Helvetica',7); canvas.setFillColor(colors.HexColor('#64748b')); canvas.drawString(16*mm,7*mm,'SolarKenya Pro • Generated by SolarOps'); canvas.drawRightString(194*mm,7*mm,f'Page {doc_.page}'); canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return path

st.set_page_config(page_title='SolarKenya Pro | SolarOps',page_icon='☀️',layout='wide')
st.markdown('''<style>
.stApp{background:#f4f7fb}.block-container{padding-top:1.2rem;max-width:1500px}.sk-header{background:#0b1e38;color:white;padding:18px 22px;border-radius:12px;margin-bottom:16px}.sk-header h1{color:white;margin:0;font-size:26px}.sk-header p{color:#c8d8eb;margin:3px 0 0}.metric-card{background:white;border:1px solid #e0e8f2;border-radius:10px;padding:14px}.stButton>button{border-radius:8px;font-weight:600}
</style>''',unsafe_allow_html=True)
con=db()
if 'company' not in st.session_state: st.session_state.company=COMPANY_DEFAULT.copy()
company=st.session_state.company
with st.sidebar:
    st.markdown('## ☀️ SolarKenya Pro')
    st.caption('Smarter Solar. Brighter Tomorrow.')
    page=st.radio('Navigation',['Dashboard','Customers','Projects & Sites','Documents & Billing','Inventory','Maintenance','Reports','Company Settings'],label_visibility='collapsed')
    st.divider(); st.metric('CO₂ avoided (demo)', '842.5 t'); st.caption('Demo indicator — connect verified generation data for live calculations.')

st.markdown('<div class="sk-header"><h1>SolarKenya Pro</h1><p>Integrated solar operations, projects, assets and document management</p></div>',unsafe_allow_html=True)

def doc_table():
    rows=con.execute('SELECT number,doc_type,customer,issue_date,due_date,status,total,currency FROM documents ORDER BY id DESC LIMIT 100').fetchall()
    if rows:
        st.dataframe([dict(r) for r in rows],use_container_width=True,hide_index=True)
    else: st.info('No documents yet. Create a quotation or invoice to get started.')

if page=='Dashboard':
    docs=con.execute('SELECT COUNT(*) n, COALESCE(SUM(total),0) total FROM documents').fetchone()
    open_docs=con.execute("SELECT COUNT(*) n FROM documents WHERE status IN ('Draft','Sent','Overdue')").fetchone()['n']
    customers=con.execute('SELECT COUNT(DISTINCT customer) n FROM documents').fetchone()['n']
    c1,c2,c3,c4=st.columns(4)
    c1.metric('Documents created',docs['n']); c2.metric('Document value',money(docs['total'])); c3.metric('Open documents',open_docs); c4.metric('Customers served',customers)
    st.subheader('Recent documents'); doc_table()
    st.caption('This dashboard is driven by records stored in the local SQLite database. Energy, sites and asset KPIs remain unavailable until operational data is entered or integrations are configured.')
elif page=='Documents & Billing':
    st.subheader('Document centre')
    with st.expander('＋ Create a document',expanded=True):
        with st.form('document_form',clear_on_submit=False):
            a,b,c=st.columns(3)
            dtype=a.selectbox('Document type',DOC_TYPES)
            customer=b.text_input('Customer / organisation *',placeholder='e.g. Kibera Solar Hub Ltd')
            currency=c.selectbox('Currency',['KES','USD','EUR','GBP'])
            a,b,c=st.columns(3); issue=a.date_input('Issue date',date.today()); due=b.date_input('Due date',date.today()+timedelta(days=30)); status=c.selectbox('Status',['Draft','Sent','Approved','Paid','Partially Paid','Overdue','Cancelled'])
            a,b,c=st.columns(3); email=a.text_input('Customer email'); phone=b.text_input('Customer phone'); address=c.text_input('Customer address')
            vat=st.number_input('VAT rate (%)',min_value=0.0,max_value=100.0,value=16.0,step=0.5)
            st.markdown('**Line items** (add one row per product or service)')
            items=[]
            for i in range(1,7):
                cols=st.columns([5,1,2])
                desc=cols[0].text_input(f'Description {i}',key=f'desc_{i}',placeholder='Solar panel, installation, maintenance…')
                qty=cols[1].number_input(f'Qty {i}',min_value=0.0,value=1.0 if i==1 else 0.0,step=1.0,key=f'qty_{i}')
                price=cols[2].number_input(f'Unit price {i} ({currency})',min_value=0.0,value=0.0,step=100.0,key=f'price_{i}')
                if desc.strip() and qty>0: items.append({'description':desc.strip(),'qty':qty,'unit_price':price})
            notes=st.text_area('Notes, payment terms or scope',placeholder='Payment due within 30 days…')
            submitted=st.form_submit_button('Generate and save document',type='primary',use_container_width=True)
        if submitted:
            if not customer.strip(): st.error('Enter a customer or organisation name.')
            elif not items: st.error('Add at least one line item with a description and quantity greater than zero.')
            else:
                clean,subtotal,tax,total=calc(items,vat)
                number=next_number(con,dtype)
                payload={'number':number,'doc_type':dtype,'customer':customer.strip(),'customer_email':email,'customer_phone':phone,'customer_address':address,'issue_date':str(issue),'due_date':str(due),'status':status,'currency':currency,'vat_rate':vat,'notes':notes,'items':clean,'subtotal':subtotal,'tax':tax,'total':total}
                path=make_pdf(payload,company)
                con.execute('INSERT INTO documents(number,doc_type,customer,customer_email,customer_phone,customer_address,issue_date,due_date,status,currency,vat_rate,notes,items_json,subtotal,tax,total,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(number,dtype,customer.strip(),email,phone,address,str(issue),str(due),status,currency,vat,notes,json.dumps(clean),subtotal,tax,total,datetime.now().isoformat(timespec='seconds')))
                con.commit(); st.session_state['last_pdf']=str(path); st.session_state['last_number']=number
                st.success(f'{dtype} {number} generated and saved. Total: {money(total,currency)}')
    if st.session_state.get('last_pdf') and Path(st.session_state['last_pdf']).exists():
        p=Path(st.session_state['last_pdf']); st.download_button('⬇ Download latest PDF',data=p.read_bytes(),file_name=p.name,mime='application/pdf',use_container_width=True)
        st.info('To print: download the PDF and print it from your PDF viewer. The PDF is formatted for A4 paper.')
    st.subheader('Document register'); doc_table()
    with st.expander('Open or download a previously generated PDF'):
        rows=con.execute('SELECT number,doc_type,customer FROM documents ORDER BY id DESC').fetchall()
        choices={f"{r['number']} · {r['doc_type']} · {r['customer']}":r['number'] for r in rows}
        if choices:
            selected=st.selectbox('Select document',list(choices))
            fp=OUT_DIR/f"{choices[selected]}.pdf"
            if fp.exists(): st.download_button('Download selected PDF',fp.read_bytes(),file_name=fp.name,mime='application/pdf')
            else: st.warning('PDF file is missing from generated_documents; regenerate from the source record in a future version.')
elif page=='Company Settings':
    st.subheader('Company profile and document branding')
    st.caption('These details appear on newly generated PDFs. Configure them before issuing documents to customers.')
    with st.form('company_settings'):
        company['name']=st.text_input('Registered business name',company['name'])
        company['address']=st.text_area('Postal / physical address',company['address'])
        c1,c2=st.columns(2); company['phone']=c1.text_input('Business phone',company['phone']); company['email']=c2.text_input('Business email',company['email'])
        c1,c2=st.columns(2); company['pin']=c1.text_input('KRA PIN',company['pin']); company['bank']=c2.text_input('Bank name',company['bank'])
        c1,c2=st.columns(2); company['account']=c1.text_input('Bank account / payment reference',company['account']); company['mpesa_paybill']=c2.text_input('M-Pesa Paybill / Till',company['mpesa_paybill'])
        if st.form_submit_button('Save company profile',type='primary'): st.session_state.company=company; st.success('Company details saved for this app session. Add persistent configuration before production deployment.')
elif page=='Customers':
    st.subheader('Customer directory')
    with st.expander('Add customer', expanded=True):
        with st.form('add_customer'):
            c1,c2=st.columns(2); nm=c1.text_input('Customer / organisation *'); em=c2.text_input('Email'); c3,c4=st.columns(2); ph=c3.text_input('Phone'); pin=c4.text_input('KRA PIN (optional)'); addr=st.text_area('Address')
            if st.form_submit_button('Save customer',type='primary'):
                if not nm.strip(): st.error('Customer name is required.')
                else:
                    con.execute('INSERT INTO customers(name,email,phone,address,pin,created_at) VALUES(?,?,?,?,?,?)',(nm.strip(),em,ph,addr,pin,datetime.now().isoformat(timespec='seconds'))); con.commit(); st.success('Customer saved.')
    rows=con.execute('SELECT id,name,email,phone,address,pin,created_at FROM customers ORDER BY name').fetchall()
    if rows: st.dataframe([dict(r) for r in rows],use_container_width=True,hide_index=True)
    else: st.info('No customers saved yet. Add a customer above; document creation can also capture bill-to details.')
elif page=='Projects & Sites':
    st.subheader('Projects & sites')
    customer_rows=con.execute('SELECT name FROM customers ORDER BY name').fetchall(); customer_names=['—']+[r['name'] for r in customer_rows]
    with st.expander('Create project / site',expanded=True):
        with st.form('add_project'):
            a,b,c=st.columns(3); pname=a.text_input('Project / site name *'); pcust=b.selectbox('Customer',customer_names); loc=c.text_input('Location / county'); a,b,c=st.columns(3); kw=a.number_input('System size (kWp)',min_value=0.0,step=1.0); budget=b.number_input('Approved budget (KES)',min_value=0.0,step=10000.0); status=c.selectbox('Status',['Lead','Survey','Design','Quoted','Approved','Procurement','Installation','Commissioning','Completed','On Hold'])
            a,b=st.columns(2); start=a.date_input('Start date',date.today()); target=b.date_input('Target completion',date.today()+timedelta(days=30)); notes=st.text_area('Scope / notes')
            if st.form_submit_button('Save project',type='primary'):
                if not pname.strip(): st.error('Project name is required.')
                else:
                    con.execute('INSERT INTO projects(name,customer,site_location,system_kw,budget,status,start_date,target_date,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(pname.strip(),'' if pcust=='—' else pcust,loc,kw,budget,status,str(start),str(target),notes,datetime.now().isoformat(timespec='seconds'))); con.commit(); st.success('Project saved.')
    rows=con.execute('SELECT id,name,customer,site_location,system_kw,budget,status,start_date,target_date FROM projects ORDER BY id DESC').fetchall()
    if rows: st.dataframe([dict(r) for r in rows],use_container_width=True,hide_index=True)
    else: st.info('No projects yet. Create one above.')
elif page=='Inventory':
    st.subheader('Inventory & reorder control')
    with st.expander('Add / receive stock',expanded=True):
        with st.form('add_stock'):
            a,b,c=st.columns(3); sku=a.text_input('SKU / code *'); item=b.text_input('Item name *'); cat=c.selectbox('Category',['Solar panel','Inverter','Battery','Mounting','Cable & protection','Meter / monitoring','Tools','Other']); a,b,c=st.columns(3); qty=a.number_input('Quantity on hand',min_value=0.0,step=1.0); reorder=b.number_input('Reorder level',min_value=0.0,step=1.0); cost=c.number_input('Unit cost (KES)',min_value=0.0,step=100.0); a,b=st.columns(2); loc=a.text_input('Warehouse / branch'); supplier=b.text_input('Supplier')
            if st.form_submit_button('Save inventory item',type='primary'):
                if not sku.strip() or not item.strip(): st.error('SKU and item name are required.')
                else:
                    try: con.execute('INSERT INTO inventory(sku,item_name,category,quantity,reorder_level,unit_cost,location,supplier,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(sku.strip(),item.strip(),cat,qty,reorder,cost,loc,supplier,datetime.now().isoformat(timespec='seconds'))); con.commit(); st.success('Inventory item saved.')
                    except sqlite3.IntegrityError: st.error('That SKU already exists. Use a unique SKU.')
    rows=con.execute('SELECT sku,item_name,category,quantity,reorder_level,unit_cost,location,supplier FROM inventory ORDER BY item_name').fetchall()
    if rows:
        st.dataframe([dict(r) for r in rows],use_container_width=True,hide_index=True)
        low=[dict(r) for r in rows if r['quantity']<=r['reorder_level']]
        if low: st.warning(f'{len(low)} item(s) are at or below their reorder level.'); st.dataframe(low,use_container_width=True,hide_index=True)
    else: st.info('No inventory items yet.')
elif page=='Maintenance':
    st.subheader('Maintenance & service tickets')
    with st.expander('Create service ticket',expanded=True):
        with st.form('add_ticket'):
            a,b,c=st.columns(3); customer= a.text_input('Customer / organisation'); site=b.text_input('Site / asset'); priority=c.selectbox('Priority',['Low','Normal','High','Critical']); issue=st.text_area('Issue / work requested *'); a,b,c=st.columns(3); assigned=a.text_input('Assigned technician'); due=b.date_input('Due date',date.today()+timedelta(days=2)); status=c.selectbox('Status',['Open','Assigned','In Progress','Waiting for Parts','Resolved','Closed']); notes=st.text_area('Diagnosis / notes')
            if st.form_submit_button('Create ticket',type='primary'):
                if not issue.strip(): st.error('Issue description is required.')
                else:
                    n=f'SRV-{date.today().year}-{datetime.now().strftime("%m%d%H%M%S")}'; con.execute('INSERT INTO service_tickets(ticket_no,customer,site,issue,priority,status,assigned_to,due_date,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(n,customer,site,issue,priority,status,assigned,str(due),notes,datetime.now().isoformat(timespec='seconds'))); con.commit(); st.success(f'Service ticket {n} created.')
    rows=con.execute('SELECT ticket_no,customer,site,issue,priority,status,assigned_to,due_date,notes FROM service_tickets ORDER BY CASE priority WHEN "Critical" THEN 1 WHEN "High" THEN 2 ELSE 3 END, due_date').fetchall()
    if rows: st.dataframe([dict(r) for r in rows],use_container_width=True,hide_index=True)
    else: st.info('No service tickets yet.')
elif page=='Reports':
    st.subheader('Document and billing report')
    rows=con.execute('SELECT doc_type, status, COUNT(*) documents, SUM(subtotal) subtotal, SUM(tax) tax, SUM(total) total FROM documents GROUP BY doc_type,status ORDER BY doc_type,status').fetchall()
    if rows: st.dataframe([dict(r) for r in rows],use_container_width=True,hide_index=True)
    else: st.info('Create documents to populate reports.')

con.close()
