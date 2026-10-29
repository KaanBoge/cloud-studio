from pathlib import Path
import json
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, Color
P=Path(__file__).resolve().parent
series=json.loads((P/'contrast_series.json').read_text())
colors={'Enzo E':'#117a88','Enzo':'#d17c1f','Athena++':'#4b854b','AthenaPK HLLE/PLM*':'#684c9c','AthenaPK HLLC/PPM*':'#a3487c'}
c=canvas.Canvas(str(P/'figures/contrast_histories_updated.pdf'),pagesize=(648,230))
c.setTitle('Dense mass histories across initial density contrasts')
for panel,chi in enumerate([10,1000]):
 x0,y0,w,h=48+panel*317,36,270,163
 c.setFont('Helvetica',10);c.setFillColorRGB(0,0,0);c.drawCentredString(x0+w/2,215,f'Density contrast = {chi}')
 c.setLineWidth(.4)
 for i in range(7):
  y=y0+h*i/6;c.setStrokeColor(Color(.88,.88,.88));c.line(x0,y,x0+w,y)
  c.setFont('Helvetica',8);c.setFillColorRGB(0,0,0);c.drawRightString(x0-7,y-3,f'{i*.2:.1f}')
 for i in range(6):
  x=x0+w*i/5;c.setStrokeColorRGB(0,0,0);c.line(x,y0,x,y0-3);c.drawCentredString(x,y0-14,str(i))
 c.setStrokeColorRGB(0,0,0);c.line(x0,y0,x0+w,y0);c.line(x0,y0,x0,y0+h)
 c.setFont('Helvetica',9);c.drawCentredString(x0+w/2,6,'Time / initial cloud-crushing time')
 for k,row in enumerate(x for x in series if x['chi']==chi):
  c.setStrokeColor(HexColor(colors[row['label']]));c.setLineWidth(1.2);p=c.beginPath()
  for i,(t,d) in enumerate(zip(row['times'],row['dense'])):
   (p.moveTo if i==0 else p.lineTo)(x0+w*t/5,y0+h*d/1.2)
  c.drawPath(p)
  ly=y0+63-k*12 if chi==10 else y0+h-11-k*12
  lx=x0+12 if chi==10 else x0+160
  c.line(lx,ly,lx+16,ly);c.setFillColorRGB(0,0,0);c.setFont('Helvetica',7);c.drawString(lx+21,ly-2.5,row['label'])
c.saveState();c.translate(12,118);c.rotate(90);c.setFont('Helvetica',9);c.drawCentredString(0,0,'Dense-mass fraction');c.restoreState();c.save()
