from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import mm
COMPANY_DEFAULT={'name':'SolarKenya Pro Ltd','address':'P.O. Box 12345-00100, Nairobi, Kenya','phone':'+254 700 123 456','email':'accounts@example.co.ke','pin':'','bank':'','account':'','mpesa_paybill':''}
def calc(items,vat_rate):
    clean=[]
    for it in items:
        qty=max(0,float(it.get('qty',0))); price=max(0,float(it.get('unit_price',0)))
        clean.append({**it,'qty':qty,'unit_price':price,'amount':round(qty*price,2)})
    subtotal=round(sum(i['amount'] for i in clean),2); tax=round(subtotal*float(vat_rate)/100,2)
    return clean,subtotal,tax,round(subtotal+tax,2)
def make_pdf(payload,company,out_dir):
    out_dir=Path(out_dir); out_dir.mkdir(parents=True,exist_ok=True); path=out_dir/f"{payload['number']}.pdf"
    styles=getSampleStyleSheet(); story=[]
    story.append(Paragraph(company['name'],styles['Title'])); story.append(Paragraph(f"{payload['doc_type'].upper()} — {payload['number']}",styles['Heading1']))
    story.append(Paragraph(f"{company['address']}<br/>{company['phone']} · {company['email']}<br/>KRA PIN: {company.get('pin') or 'Not configured'}",styles['Normal'])); story.append(Spacer(1,12))
    story.append(Paragraph(f"<b>Customer:</b> {payload['customer']}<br/>{payload.get('customer_address','')}<br/><b>Issue date:</b> {payload['issue_date']} &nbsp;&nbsp; <b>Due:</b> {payload.get('due_date','—')}<br/><b>Status:</b> {payload['status']}",styles['Normal'])); story.append(Spacer(1,12))
    rows=[['#','Description','Qty','Unit price','Amount']]
    for i,it in enumerate(payload['items'],1): rows.append([str(i),str(it['description']),f"{it['qty']:g}",f"{payload['currency']} {it['unit_price']:,.2f}",f"{payload['currency']} {it['amount']:,.2f}"])
    t=Table(rows,colWidths=[10*mm,80*mm,15*mm,32*mm,33*mm],repeatRows=1); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8f1fb')),('GRID',(0,0),(-1,-1),.4,colors.grey),('ALIGN',(2,1),(-1,-1),'RIGHT'),('VALIGN',(0,0),(-1,-1),'TOP'),('PADDING',(0,0),(-1,-1),6)])); story.append(t); story.append(Spacer(1,12))
    totals=[['Subtotal',f"{payload['currency']} {payload['subtotal']:,.2f}"],[f"VAT ({payload['vat_rate']}%)",f"{payload['currency']} {payload['tax']:,.2f}"],['TOTAL',f"{payload['currency']} {payload['total']:,.2f}"]]
    t=Table(totals,colWidths=[50*mm,45*mm],hAlign='RIGHT'); t.setStyle(TableStyle([('ALIGN',(1,0),(1,-1),'RIGHT'),('FONTNAME',(0,-1),(-1,-1),'Helvetica-Bold'),('BACKGROUND',(0,-1),(-1,-1),colors.HexColor('#e8f1fb')),('PADDING',(0,0),(-1,-1),6)])); story.append(t)
    if payload.get('notes'): story += [Spacer(1,14),Paragraph('<b>Notes / terms</b>',styles['Heading3']),Paragraph(payload['notes'].replace('\n','<br/>'),styles['Normal'])]
    doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=16*mm,leftMargin=16*mm,topMargin=15*mm,bottomMargin=15*mm); doc.build(story); return path
