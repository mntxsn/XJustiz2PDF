#!/usr/bin/python3
# coding: utf-8
from lookup import Lookup as Lookup
import lxml.etree as ET 
import re
from os import path
import sys  

# Pfade und Dateien
script_path = path.dirname(path.realpath(__file__))
filepath= script_path + "/lookups/"
lookup=Lookup(filepath)

inputfile = script_path + "/testdata/XJustiz_2_4_0.xml"
inputfile = script_path + "/testdata/Beispiel_synthetisch2.xml"
#inputfile = script_path + "/testdata/xjustiz_nachricht_v3_2.xml"

outfile = "./output.pdf"
# Standardnamespace
xj_ns='{http://www.xjustiz.de}'
newline='\n'
# Wo liegen XML, XSD-Dateien mit Codelisten?
lookup=Lookup(filepath)

XMLinput = ET.parse(inputfile)
root=XMLinput.getroot()

# Setzt Namespace hinter /
def addNS(path, namespace=xj_ns):
    return re.sub( "/(?!/)", "/" + namespace , path)

# Wie "find", liest jedoch gleich .text aus
# code=True hängt "/code" ohne Namespace and den Pfad 
def findElementText(path, element=root, namespace=xj_ns, code=False):
    path = addNS(path)
    if code: path += '/code'
    try:
        return element.find(path).text
    except AttributeError:
        return ''

def getElementText(path, element=root, namespace=xj_ns):
    path = addNS(path)
    try:
        return element.get(path).text
    except AttributeError:
        return ''

# Gibt alle Textelemente der mit findall gefundenen Elemente
# mit Newline getrennt als string zurück
def getSubTexts (path, element=root, namespace=xj_ns, newline='\n'):
    path = addNS(path)
    text=''
    try:
        for child in element.findall(path):
            if text=='':
                text=child.text
            else:
                text+= newline+child.text    
        return text
    except AttributeError:
        return text

# Wie find, fügt jedoch automatisch Namespace zu Pfad hinzu
def findElement (path, element=root, namespace=xj_ns):
    path = addNS(path)
    try:
        return element.find(path)
    except AttributeError:
        return ''

# Wie findAll, fügt jedoch automatisch Namespace zu Pfad hinzu
def findAllElements (path, element=root, namespace=xj_ns, code=False):
    path = addNS(path)
    if code: path += '/code'
    try:
        return element.findall(path)
    except AttributeError:
        return ''

# Prüft, ob ein übergebener Tag im Ergebnis-Node von find vorhanden ist
def tagInAuswahl (tag, auswahl, namespace=xj_ns):
    if auswahl is not None:
        for child in auswahl:
            if child.tag == namespace + tag:
                return True
    return False

def parseOrganisation(node):
    orgData={}
    orgData['type']='GDS.Organisation'
    orgData['bezeichnung.aktuell']=findElementText('./bezeichnung/bezeichnung.aktuell', node)
    orgData['kurzbezeichnung']    =findElementText('./kurzbezeichnung', node)
    orgData['bezeichnung.alt']=[]
    for bezeichnung in findAllElements ('./bezeichnung/bezeichnung.alt', node): 
        orgData['bezeichnung.alt'].append(bezeichnung.text)
    
    orgData['anschrift']=[]
    for anschrift in findAllElements ("./anschrift", node): 
        orgData['anschrift'].append(parseAnschrift(anschrift)) 
    
    orgData['geschlecht']    =lookup.xjustizValue ('GDS.Geschlecht', findElementText("./geschlecht", node, code=True))
    
    orgData['telekommunikation']=[]
    for telekom in findAllElements ("./telekommunikation", node): 
        orgData['telekommunikation'].append(parseTelekommunikation(telekom))
    
    orgData['umsatzsteuerID']= findElementText('./umsatzsteuerID', node)
    
    return orgData

def parseKanzlei(node):
    kanzleiData={}
    kanzleiData['type']='GDS.RA.Kanzlei'
    kanzleiData['bezeichnung.aktuell']=findElementText('./bezeichnung/bezeichnung.aktuell', node)
    kanzleiData['bezeichnung.alt']=[]
    for bezeichnung in findAllElements ('./bezeichnung/bezeichnung.alt', node): 
        kanzleiData['bezeichnung.alt'].append(bezeichnung.text)
    
    kanzleiData['anschrift']=[]
    for anschrift in findAllElements ("./anschrift", node): 
        kanzleiData['anschrift'].append(parseAnschrift(anschrift)) 
    
    kanzleiData['geschlecht'] =lookup.xjustizValue ('GDS.Geschlecht', findElementText("./geschlecht", node, code=True))
    kanzleiData['rechtsform'] =lookup.xjustizValue ('GDS.Rechtsform', findElementText("./rechtsform", node, code=True))
    kanzleiData['kanzleiform']=lookup.xjustizValue ('GDS.Kanzleiform', findElementText("./kanzleiform", node, code=True))
    
    kanzleiData['telekommunikation']=[]
    for telekom in findAllElements ("./telekommunikation", node): 
        kanzleiData['telekommunikation'].append(parseTelekommunikation(telekom))
    
    kanzleiData['raImVerfahren']=parseNatuerlichePerson(findElement('./raImVerfahren', node))
    
    kanzleiData['umsatzsteuerID']= findElementText('./umsatzsteuerID', node)
    return kanzleiData

def parseNatuerlichePerson(node):
    personData={}
    personData['type']='GDS.NatuerlichePerson'
    personData['vollerName']=parseNameNatuerlichePerson(findElement('./vollerName', node))
    
    personData['aliasNatuerlichePerson']=[]
    for alias in findAllElements ("./aliasNatuerlichePerson", node): 
        personData['aliasNatuerlichePerson'].append(parseNatuerlichePerson(alias))
    
    personData['umsatzsteuerID']= findElementText('./umsatzsteuerID', node)
    
    personData['geschlecht']    =lookup.xjustizValue ('GDS.Geschlecht', findElementText("./geschlecht", node, code=True))
    personData['familienstand'] =lookup.xjustizValue ('GDS.Familienstand', findElementText("./familienstand", node, code=True))
    personData['personalstatut']=lookup.xjustizValue ('GDS.Personalstatut', findElementText("./personalstatut", node, code=True))
    
    personData['beruf']=[]
    for beruf in findAllElements ("./beruf", node): 
        personData['beruf'].append(beruf.text)
    
    personData['telekommunikation']=[]
    for telekom in findAllElements ("./telekommunikation", node): 
        personData['telekommunikation'].append(parseTelekommunikation(telekom))
        
    personData['anschrift']=[]
    for anschrift in findAllElements ("./anschrift", node): 
        personData['anschrift'].append(parseAnschrift(anschrift))    
    
    personData['zustaendigeInstitution']=[]
    for institution in findAllElements ("./zustaendigeInstitution/ref.rollennummer", node): 
        personData['zustaendigeInstitution'].append(institution.text)      
    return personData

def parseAnschrift(node):
    pass

def parseNameNatuerlichePerson(node):
    namensbestandteile={}
    
    simpleValues=(  
            'vorname',
            'rufname',
            'titel',
            'nachname',
            'geburtsname',
            'namenszusatz',
            'geburtsnamensvorsatz',            
        )
    for simpleValue in simpleValues:
        namensbestandteile[simpleValue] = findElementText('./'+simpleValue, node)
    
    multiValues=(  
            'vorname.alt',
            'nachname.alt',
            'weitererName'            
        )    
    for multiValue in multiValues:    
        namensbestandteile[multiValue] = []
        for value in findAllElements ("./"+multiValue, node):  
            namensbestandteile[multiValue].append(value.text)       
            
    return namensbestandteile

def parseBeteiligung(beteiligungNode):
    beteiligung={}
    beteiligung['rolle']=[]
    for rolle in findAllElements ("./rolle", beteiligungNode):
        rolleData={}
        rolleData['rollennummer']= findElementText("./rollennummer", rolle)
        rolleData['nr']= findElementText("./nr", rolle)
        rolleData['geschaeftszeichen']= findElementText("./geschaeftszeichen", rolle)
        rolleData['naehereBezeichnung']= findElementText("./naehereBezeichnung", rolle)
        rolleData['rollenbezeichnung']=lookup.xjustizValue ('GDS.Rollenbezeichnung', findElementText("./rollenbezeichnung", rolle, code=True))
        
        rolleData['referenz']=[]
        for referenz in findAllElements ("./referenz", rolle): 
            rolleData['referenz'].append(findElementText("./ref.rollennummer", referenz))
        
        rolleData['rollenID']=[]
        for rollenID in findAllElements ("./rollenID", rolle): 
            rollenIDData={}
            rollenIDData['id']=findElementText("./id", rollenID)
            rollenIDData['ref.instanznummer']=findElementText("./ref.instanznummer", rollenID)
            rolleData['rollenID'].append(rollenIDData)
                
        beteiligung['rolle'].append(rolleData)
        
    beteiligung['beteiligtennummer']=findElementText("./beteiligter/beteiligtennummer", beteiligungNode)
    beteiligterAuswahl              =findElement("./beteiligter/auswahl_beteiligter", beteiligungNode)
    if   tagInAuswahl ('ra.kanzlei', beteiligterAuswahl):
        beteiligung['beteiligter']  = parseKanzlei(findElement('./ra.kanzlei',beteiligterAuswahl))
    elif tagInAuswahl ('natuerlichePerson', beteiligterAuswahl):
        beteiligung['beteiligter']  = parseNatuerlichePerson(findElement('./natuerlichePerson',beteiligterAuswahl))
    elif tagInAuswahl ('organisation', beteiligterAuswahl):
        beteiligung['beteiligter']  = parseOrganisation(findElement('./organisation',beteiligterAuswahl))
    else:
        beteiligung['beteiligter']  = {}
    
    print(beteiligung)
    return beteiligung

def parseVerfahrensgegenstand(node):
    gegenstandData={}
    gegenstandData['gegenstand']     =findElementText('.//gegenstand', node)
    gegenstandData['gegenstandswert']=findElementText('.//zahl', node) + ' ' + lookup.xjustizValue ('Währung', findElementText(".//waehrung", element=node, code=True))
    
    gegenstandData['auswahl_zeitraumDesVerwaltungsaktes']=''
    auswahl = findElement("./auswahl_zeitraumDesVerwaltungsaktes", node)
    if   tagInAuswahl ('jahr', auswahl):
        gegenstandData['auswahl_zeitraumDesVerwaltungsaktes']=findElementText(".//jahr", node)
    elif tagInAuswahl ('stichtag', auswahl):
        gegenstandData['auswahl_zeitraumDesVerwaltungsaktes']=findElementText(".//stichtag", node)
    elif tagInAuswahl ('keinZeitraum', auswahl):
        gegenstandData['auswahl_zeitraumDesVerwaltungsaktes']=findElementText(".//keinZeitraum", node)        
    elif tagInAuswahl ('zeitraum', auswahl):
        gegenstandData['auswahl_zeitraumDesVerwaltungsaktes']=findElementText(".//beginn", node) + ' ' + findElementText(".//ende", node)
    
    return gegenstandData

def parseBehoerde(auswahlNode):
    behoerde={}
    if   tagInAuswahl ('sonstige', auswahlNode):
        behoerde['name'] = findElementText("./sonstige", auswahlNode)
        behoerde['type'] = 'sonstige'
    elif tagInAuswahl ('gericht', auswahlNode):
        behoerde['name'] = lookup.xjustizValue ('GDS.Gerichte', findElementText("./gericht",auswahlNode , code=True))
        behoerde['type'] ='GDS.Gerichte'
    elif tagInAuswahl ('beteiligter', auswahlNode):
        behoerde['name'] = findElementText("./beteiligter/ref.beteiligtennummer", auswahlNode)
        behoerde['type'] ='GDS.Ref.Beteiligtennummer'
    return behoerde 

def parseAktenzeichen(aktenzeichen):
    aktenzeichenParts={}
    aktenzeichenParts['az.art']                      =lookup.xjustizValue ('GDS.Aktenzeichenart', findElementText("./az.art", element=aktenzeichen, code=True))
    aktenzeichenParts['auswahl_az.vergebendeStation']=parseBehoerde(findElement("./auswahl_az.vergebendeStation", element=aktenzeichen))
    #TESTEN!!!!
    aktenzeichenParts['aktenzeichen.freitext']       =findElementText("./auswahl_aktenzeichen/aktenzeichen.freitext", element=aktenzeichen) 
    if len(aktenzeichenParts['aktenzeichen.freitext'])==0:
        aktenzeichenStrukturiert={}
        aktenzeichenElements=(  
            'sachgebietsschluessel',
            'zusatzkennung',
            'abteilung',
            'laufendeNummer',
            'jahr',
            'vorsatz',
            'zusatz',
            'dezernat',
            'erfassungsdatum'                       
        )
        for elementName in aktenzeichenElements:
            aktenzeichenStrukturiert[elementName]=findElementText(".//" + elementName, element=aktenzeichen)
        aktenzeichenStrukturiert['register']     =lookup.xjustizValue ('GDS.Registerzeichen', findElementText(".//register", element=aktenzeichen, code=True))
        aktenzeichenParts['aktenzeichen.strukturiert']=aktenzeichenStrukturiert
    return aktenzeichenParts

def parseTelekommunikation(node):
    telkodata={}
    telkodata['telekommunikationsart']   =lookup.xjustizValue ('GDS.Telekommunikationsart', findElementText("./telekommunikationsart", node, code=True))
    telkodata['telekommunikationszusatz']=lookup.xjustizValue ('GDS.Telekommunikationszusatz', findElementText("./telekommunikationszusatz", node, code=True))
    telkodata['verbindung']              =findElementText('.//verbindung', node)
    return telkodata

# funktion def parseDokumente(docNode) returns dict
def parseDokumente(path='./schriftgutobjekte/dokument', element=root):
    documents={}
    documentNodes=findAllElements(path, element=element)
    if documentNodes != '':
        simpleValues=(  
            'id',
            'nummerImUebergeordnetenContainer',
            'fremdesGeschaeftszeichen',
            'posteingangsdatum',
            'datumDesSchreibens',
            'anzeigename',
            'akteneinsicht',
            'veraktungsdatum',
            'absenderAnzeigename',
            'adressatAnzeigename',
            'justizkostenrelevanz',
            'ruecksendungEEB.erforderlich',
            'zustellung41StPO',
        )
        for documentNode in documentNodes:
            document={}
            
            for simpleValue in simpleValues:
                document[simpleValue]=findElementText('.//'+simpleValue, documentNode)
            
            document['vertraulichkeitsstufe']=lookup.xjustizValue ('Vertraulichkeitsstufe', findElementText(".//vertraulichkeitsstufe", element=documentNode , code=True)) 
            document['dokumentklasse']       =lookup.xjustizValue ('GDS.Dokumentklasse', findElementText(".//dokumentklasse", element=documentNode , code=True)) 
            document['dokumententyp']        =lookup.xjustizValue ('GDS.Dokumenttyp', findElementText(".//dokumententyp", element=documentNode , code=True))  
            
            document['personen']=[]
            for person in findAllElements('.//person/ref.beteiligtennummer', element=documentNode):
                document['personen'].append(person.text)
            
            document['verweise']=[]
            for verweis in findAllElements('.//verweis', element=documentNode):
                verweisParts={}
                verweisParts['anzeigenameSGO']=findElementText('./anzeigenameSGO', element=verweis)
                verweisParts['id.sgo']        =findElementText('./id.sgo', element=verweis)
                verweisParts['verweistyp']    =lookup.xjustizValue ('GDS.Verweistyp', findElementText("./verweistyp", element=verweis , code=True))   
                document['verweise'].append(verweisParts)
            
            document['dateien']=[]
            for datei in findAllElements('.//datei', element=documentNode):
                dateiData={}
                dateiData['dateiname']     =findElementText('./dateiname', element=datei)
                dateiData['versionsnummer']=findElementText('./versionsnummer', element=datei)
                dateiData['bestandteil']   =lookup.xjustizValue ('GDS.Bestandteiltyp', findElementText("./bestandteil", element=datei , code=True))  
                
                dateiData['dateiname.bezugsdatei']=[]
                for bezugsdatei in findAllElements ('./dateiname.bezugsdatei', element=datei):
                    dateiData['dateiname.bezugsdatei'].append(bezugsdatei.text)
                
                document['dateien'].append(dateiData)
            
            documents[document['id']]=document
    return documents

# funktion def parseDokumente(docNode) returns dict
def parseAkten(path='./schriftgutobjekte/akte', element=root):
    files={}
    fileNodes=findAllElements(path, element=element)
    if fileNodes != '':
        simpleValues=(  
            './anzeigename',
            './identifikation/id',
            './identifikation/nummerImUebergeordnetenContainer',
            './xjustiz.fachspezifischeDaten/anzeigename',
            './xjustiz.fachspezifischeDaten/weiteresOrdnungskriteriumBehoerde',
            './xjustiz.fachspezifischeDaten/erstellungszeitpunktAkteVersand',
            './xjustiz.fachspezifischeDaten/ruecksendungEEB.erforderlich',
            './xjustiz.fachspezifischeDaten/zustellung41StPO',
            # teilaktenspezifisch
            './xjustiz.fachspezifischeDaten/akteneinsicht',
            './xjustiz.fachspezifischeDaten/letztePaginierungProTeilakte',
        )
        for fileNode in fileNodes:
            file={}
            for simpleValue in simpleValues:
                file[simpleValue.rsplit('/', 1)[1]]=findElementText(simpleValue, fileNode)
           
            file['dokumente']           = parseDokumente('./xjustiz.fachspezifischeDaten/inhalt/dokument', fileNode)
            file['teilakten']            = parseAkten('./xjustiz.fachspezifischeDaten/inhalt/teilakte', fileNode)
            file['abgebendeStelle']      = lookup.xjustizValue ('GDS.Gerichte', findElementText("./xjustiz.fachspezifischeDaten/abgebendeStelle", element=fileNode, code=True))
            file['aktentyp']             = lookup.xjustizValue ('GDS.Aktentyp', findElementText("./xjustiz.fachspezifischeDaten/aktentyp", element=fileNode, code=True))
            file['vertraulichkeitsstufe']= lookup.xjustizValue ('Vertraulichkeitsstufe', findElementText("./vertraulichkeitsstufe", element=fileNode , code=True))
            
            file['personen']=[]
            for person in findAllElements ('./xjustiz.fachspezifischeDaten/person/ref.beteiligtennummer', element=fileNode):
                    file['personen'].append(person.text)
            
            file['laufzeit']={}
            for laufzeit in findElement ('./laufzeit', element=fileNode):
                # remove namespace and use tag as key
                file['laufzeit'][laufzeit.tag.rsplit("}", 1)[1]]=laufzeit.text
            
            file['aktenreferenzen']=[]
            for aktenreferenz in findAllElements ('./xjustiz.fachspezifischeDaten/aktenreferenzen', element=fileNode):
                referenceParts={}
                referenceParts['id.referenzierteAkte']=findElementText("./id.referenzierteAkte", element=aktenreferenz)
                referenceParts['aktenreferenzart']    =lookup.xjustizValue ('GDS.Aktenreferenzart', findElementText("./aktenreferenzart", element=aktenreferenz, code=True))
                file['aktenreferenzen'].append(referenceParts)
            
            file['aktenzeichen']=[]
            for aktenzeichen in findAllElements ('./xjustiz.fachspezifischeDaten/aktenzeichen', element=fileNode):
                 file['aktenzeichen'].append(parseAktenzeichen(aktenzeichen))
             
            # Teilaktenspezifisch
            file['teilaktentyp']=lookup.xjustizValue ('GDS.Teilaktentyp', findElementText("./xjustiz.fachspezifischeDaten/teilaktentyp", element=fileNode, code=True))
            
            files[file['id']]=file
            
    return files

####### Nachrichtenkopf (Alle Werte nach Spezifikation 3.2.1 unterstützt) #######

#sys.exit()
nachricht={}

## Allgemeine Infos
nachricht['erstellungszeitpunkt']   = findElementText("./nachrichtenkopf/erstellungszeitpunkt")
nachricht['eigeneID']               = findElementText("./nachrichtenkopf/eigeneNachrichtenID")
nachricht['fremdeID']               = findElementText("./nachrichtenkopf/fremdeNachrichtenID")
nachricht['prozessID']              = findElementText("./nachrichtenkopf/nachrichtenuebergreifenderProzess/prozessID")
nachricht['nachrichtenNummer']      = findElementText("./nachrichtenkopf/nachrichtenuebergreifenderProzess/nachrichtenNummer")
nachricht['nachrichtenAnzahl']      = findElementText("./nachrichtenkopf/nachrichtenuebergreifenderProzess/nachrichtenAnzahl")
nachricht['produktName']            = findElementText("./nachrichtenkopf/herstellerinformation/nameDesProdukts")
nachricht['produktHersteller']      = findElementText("./nachrichtenkopf/herstellerinformation/herstellerDesProdukts")
nachricht['produktVersion']         = findElementText("./nachrichtenkopf/herstellerinformation/version")
nachricht['sendungsprioritaet']     = lookup.xjustizValue ('GDS.Sendungsprioritaet', findElementText("./nachrichtenkopf/sendungsprioritaet", code=True))

nachricht['ereignisse']             = ''
for ereignis in findAllElements ("./nachrichtenkopf/ereignis", code=True):
    if len(ereignis.text)>0: 
        ereignisValue=lookup.xjustizValue ('GDS.Ereignis', ereignis.text)
        if len(nachricht['ereignisse'])>0: nachricht['ereignisse'] += newline 
        nachricht['ereignisse'] += ereignisValue

## Absenderdaten auslesen
absender = {}
absender['aktenzeichen'] = getSubTexts("./nachrichtenkopf/aktenzeichen.absender")

absenderAuswahl     = findElement("./nachrichtenkopf/auswahl_absender")

if   tagInAuswahl ('absender.sonstige', absenderAuswahl):
    absender["name"]= findElementText(".//auswahl_absender/absender.sonstige")
elif tagInAuswahl ('absender.gericht', absenderAuswahl):
    absender["name"]= lookup.xjustizValue ('GDS.Gerichte', findElementText(".//auswahl_absender/absender.gericht", code=True))
elif tagInAuswahl ('absender.rvTraeger', absenderAuswahl):
    absender["name"]= lookup.xjustizValue ('GDS.RVTraeger', findElementText(".//auswahl_absender/absender.rvTraeger", code=True))
else:
    absender["name"]=''

## Empfängerdaten auslesen
empfaenger = {}
empfaenger['aktenzeichen'] = getSubTexts("./nachrichtenkopf/aktenzeichen.empfaenger")

empfaengerAuswahl       = findElement("./nachrichtenkopf/auswahl_empfaenger")
if   tagInAuswahl ('empfaenger.sonstige', empfaengerAuswahl):
    empfaenger["name"]  = findElementText(".//auswahl_empfaenger/empfaenger.sonstige")
elif tagInAuswahl ('empfaenger.gericht', empfaengerAuswahl):
    empfaenger["name"]  = lookup.xjustizValue ('GDS.Gerichte', findElementText(".//auswahl_empfaenger/empfaenger.gericht", code=True))
elif tagInAuswahl ('empfaenger.rvTraeger', empfaengerAuswahl):
    empfaenger["name"]  = lookup.xjustizValue ('GDS.RVTraeger', findElementText(".//auswahl_empfaenger/empfaenger.rvTraeger", code=True))
else:
    empfaenger["name"]  = ''

####### Grunddaten #######

grunddaten={}
grunddaten['verfahrensnummer'] = findElementText("./grunddaten/verfahrensdaten/verfahrensnummer")

## Beteiligungen ##

grunddaten['beteiligung']=[]
for beteiligung in findAllElements ("./grunddaten/verfahrensdaten/beteiligung"):
    grunddaten['beteiligung'].append(parseBeteiligung(beteiligung))

## Instanzdaten ##
grunddaten['instanzen']=[]
simpleValues=(  
            'instanznummer',
            'sachgebietszusatz',
            'abteilung',
            'verfahrensinstanznummer',
            'kurzrubrum'            
        )
for instanz in findAllElements ("./grunddaten/verfahrensdaten/instanzdaten"):    
    instanzData={}
    for simpleValue in simpleValues:
        instanzData[simpleValue] = findElementText('.//'+simpleValue, instanz)

    instanzData['sachgebiet']    = lookup.xjustizValue ('GDS.Sachgebiet', findElementText(".//sachgebiet", element=instanz, code=True))

    instanzData['verfahrensgegenstand']=[]
    for gegenstand in findAllElements ("./verfahrensgegenstand", instanz): 
        instanzData['verfahrensgegenstand'].append(parseVerfahrensgegenstand(gegenstand))

    instanzData['telekommunikation']=[]
    for telekomEintrag in findAllElements ("./telekommunikation", instanz): 
        instanzData['telekommunikation'].append(parseTelekommunikation(telekomEintrag))
         
    instanzData['aktenzeichen']=parseAktenzeichen(findElement("./aktenzeichen", instanz))

    instanzData['auswahl_instanzbehoerde']=parseBehoerde(findElement("./auswahl_instanzbehoerde", instanz))

    grunddaten['instanzen'].append(instanzData)


## Terminsdaten ##

for termin in findAllElements ("./grunddaten/verfahrensdaten/auswahl_termin"):
    pass

####### Schriftgutobjekte #######

schriftgutobjekte={}
schriftgutobjekte['anschreiben'] = findElementText("./schriftgutobjekte/anschreiben/ref.sgo")
schriftgutobjekte['dokumente']   = parseDokumente()
schriftgutobjekte['akten']       = parseAkten()



#print(parseDokumente('./schriftgutobjekte/dokument'))
#print()
#print(parseAkten('./schriftgutobjekte/akte'))
#print(parseAkten()['96da0964-4ab8-4ee1-7777-8358abf399yy']['teilakten'])
'''
#print (absender['aktenzeichen'])xjustizValue
print (absender['name'])
print (empfaenger['name'])
#print (nachricht['erstellungszeitpunkt'])
print (nachricht['eigeneID'])
print (nachricht['produktName'])
print (nachricht['produktHersteller'])
print (grunddaten['verfahrensnummer'] )
#print (empfaenger['aktenzeichen'])
#print(lookup.rvTraeger('28'))
'''
