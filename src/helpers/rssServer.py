import os,threading,time
import rssPeriodic

while True:
      t = threading.Thread(rssPeriodic.checkForUpdates())
      t.start()
      t.join()
      time.sleep(60)
