from os import environ, getcwd
from queue import Queue
from datetime import datetime

# ======================================
# LOGGER BOT
# ======================================
TOKEN = '1044047901:AAHWb7zhMQwWiiEg266rf3ZknIiMDQHlw0Q'
CHAT_IDS = [523755114, 166462336, 192294736, 396732122]


# ======================================
# SPIDERS
# ======================================

# Hide the Firefox window when automating with selenium
environ['MOZ_HEADLESS'] = '1'

# GME urls
DOWNLOAD = getcwd()+'/downloads'
RESTRICTION = 'https://www.mercatoelettrico.org/It/Download/DownloadDati.aspx'

GME_WEEK = {
	'fname':'OfferteFree_Pubbliche',
	'url':'https://www.mercatoelettrico.org/it/Download/DownloadDati.aspx?'\
		  'val=OfferteFree_Pubbliche'
}

# Dynamic file history
START =  datetime(2017, 2, 1)
MI = {}
QUEUE = Queue()


# ======================================
# DATABASE
# ======================================

# To be changed with Polito cluster credentials
DB_NAME = "InterProj"
MONGO_HOST = "bigdatalab.polito.it"
