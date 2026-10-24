import glob
files=glob.glob('*.py')+glob.glob('src/**/*.py',recursive=True)
for fp in files:
    try:
        with open(fp,'r',encoding='latin-1') as f:
            c=f.read()
    except:
        continue
    if '\ufffd' not in c and '\xc3' not in c:
        # still try some common mojibake
        pass
    orig=c
    # common
    for old,new in [
        ('\xc3\xa1','a'),('\xc3\xa9','e'),('\xc3\xad','i'),('\xc3\xb3','o'),('\xc3\xba','u'),
        ('\xc3\x81','A'),('\xc3\x89','E'),('\xc3\x8d','I'),('\xc3\x93','O'),('\xc3\x9a','U'),
        ('\xc3\xb1','n'),('\xc3\x91','N'),
        ('Anal\xc3\xadtica','Analitica'),('Acad\xc3\xa9mica','Academica'),('Acad\xc3\xa9mico','Academico'),
        ('An\xc3\xa1lisis','Analisis'),('an\xc3\xa1lisis','analisis'),
        ('m\xc3\xa9tricas','metricas'),('M\xc3\xa9tricas','Metricas'),
        ('gr\xc3\xa1fico','grafico'),('Gr\xc3\xa1fico','Grafico'),
        ('contrase\xc3\xb1a','contrasena'),('Contrase\xc3\xb1a','Contrasena'),
        ('Informaci\xc3\xb3n','Informacion'),('informaci\xc3\xb3n','informacion'),
        ('Hist\xc3\xb3rico','Historico'),('hist\xc3\xb3rico','historico'),
        ('Gesti\xc3\xb3n','Gestion'),('decisi\xc3\xb3n','decision'),
        ('pr\xc3\xb3ximo','proximo'),('Per\xc3\xadodo','Periodo'),('per\xc3\xadodo','periodo'),
        ('p\xc3\xa1gina','pagina'),('selecci\xc3\xb3n','seleccion'),
    ]:
        c=c.replace(old,new)
    if c!=orig:
        with open(fp,'w',encoding='utf-8') as f:
            f.write(c)
        print('fixed',fp)
    else:
        # try with \\u style already read as latin-1 bytes
        pass
