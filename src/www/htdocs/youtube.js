//enter refresh time in "minutes:seconds" Minutes should range from 0 to inifinity. Seconds should range from 0 to 59'
//var limit="0:10"
if (document.images){
  var parselimit=5
}

function beginrefresh(){
  if (!document.images)
     return
  if (parselimit==1) {
       document.refreshForm.visited.value = "-1";
       makeRequest('youtube.rpy?xml=1');
       parselimit=5
       setTimeout("beginrefresh()",1000)
  }
  else{ 
     parselimit-=1
     document.refreshForm.visited.value = parselimit
     curmin=Math.floor(parselimit/60)
     cursec=parselimit%60
     if (curmin!=0)
         curtime=curmin+" minutes and "+cursec+" seconds left until page refresh!"
     else
         curtime=cursec+" seconds left until page refresh!"
     window.status=curtime
     setTimeout("beginrefresh()",1000)
  }
}
window.onload=beginrefresh

function makeRequest(url) {
    var httpRequest;

    if (window.XMLHttpRequest) { // Mozilla, Safari, ...
        httpRequest = new XMLHttpRequest();
        if (httpRequest.overrideMimeType) {
            httpRequest.overrideMimeType('text/xml');
            // See note below about this line
        }
    } 
    else if (window.ActiveXObject) { // IE
        try {
            httpRequest = new ActiveXObject("Msxml2.XMLHTTP");
        } 
        catch (e) {
            try {
                httpRequest = new ActiveXObject("Microsoft.XMLHTTP");
            } 
        catch (e) {}
        }
    }

    if (!httpRequest) {
        alert('Giving up :( Cannot create an XMLHTTP instance');
        return false;
    }
    httpRequest.onreadystatechange = function() { alertContents(httpRequest); };
    httpRequest.open('GET', url, true);
    httpRequest.send('');

}

function TableAddRow(file,filesize,percent,amtdone,speed,eta) {
    var tbl,lastrow,newrow,cellLeft;
    var textNode;

    tbl = document.getElementById("filelist")
    lastrow = tbl.rows.length;
    newrow = tbl.insertRow(lastrow);
    newrow.id = file
    newrow.className = "chanrow"

    cellLeft = newrow.insertCell(0);
    textNode = document.createTextNode("Delete");
    cellLeft.appendChild(textNode);
    cellLeft.className = "basic"

    cellLeft = newrow.insertCell(1);
    textNode = document.createTextNode(file);
    cellLeft.appendChild(textNode);
    cellLeft.className = "basic"

    cellLeft = newrow.insertCell(2);
    textNode = document.createTextNode(percent);
    cellLeft.appendChild(textNode);
    cellLeft.id = file + ".PERCENT"
    cellLeft.className = "basic"

    cellLeft = newrow.insertCell(3);
    textNode = document.createTextNode(amtdone);
    cellLeft.appendChild(textNode);
    cellLeft.id = file + ".SOFAR"
    cellLeft.className = "basic"

    cellLeft = newrow.insertCell(4);
    textNode = document.createTextNode(filesize);
    cellLeft.appendChild(textNode);
    cellLeft.id = file + ".FILESIZE"
    cellLeft.className = "basic"

    cellLeft = newrow.insertCell(5);
    textNode = document.createTextNode(speed);
    cellLeft.appendChild(textNode);
    cellLeft.id = file + ".SPEED"
    cellLeft.className = "basic"

    cellLeft = newrow.insertCell(6);
    textNode = document.createTextNode(eta);
    cellLeft.appendChild(textNode);
    cellLeft.id = file + ".ETA"
    cellLeft.className = "basic"

    lastrow = tbl.rows.length;
}

function RemoveRows(lfiles) {
    var tbl,r,cnt,rfile,fnd,xfile ;
    tbl = document.getElementById("filelist");
    
    for (r=1; r < tbl.rows.length; r++) {
        rfile = tbl.rows[r].id
        fnd = 0
        for (j=0; j < lfiles.childNodes.length; j++) {
            cfile = lfiles.childNodes[j]
            xfile = cfile.childNodes[0].firstChild.nodeValue;
            if (xfile == rfile) {
                fnd = 1
                j = lfiles.childNodes.length
            }
        }
        if (fnd == 0) {
            fnd = 1;
            tbl.deleteRow(r);
            //alert("Delete Row - " + rfile);
        }
        cnt = 0;
    }
    
}

function alertContents(httpRequest) {
    var j,cellObj;
    var cfile,filename,percent,amtdone,filesize,speed,eta;

    if (httpRequest.readyState == 4) {
        if (httpRequest.status == 200) {
                
            var filelist = httpRequest.responseXML.childNodes[0];
            for (j=0; j < filelist.childNodes.length; j++) {
                cfile = filelist.childNodes[j]
                filename = cfile.childNodes[0].firstChild.nodeValue;
                   
                percent = cfile.childNodes[1].firstChild.nodeValue;
                amtdone = cfile.childNodes[2].firstChild.nodeValue;
                filesize = cfile.childNodes[3].firstChild.nodeValue;
                speed = cfile.childNodes[4].firstChild.nodeValue;
                eta = cfile.childNodes[5].firstChild.nodeValue;

                // Check to see if a table row exists for the file.
                cellObj = document.getElementById(filename + ".FILESIZE");
                if (cellObj == null) {
                      TableAddRow(filename,filesize,percent,amtdone,speed,eta)
                }
                else {
                    cellObj = document.getElementById(filename + ".FILESIZE");
                    cellObj.childNodes[0].nodeValue=filesize;
                    cellObj = document.getElementById(filename + ".PERCENT");
                    cellObj.childNodes[0].nodeValue=percent;
                    cellObj = document.getElementById(filename + ".SOFAR");
                    cellObj.childNodes[0].nodeValue=amtdone;
                    cellObj = document.getElementById(filename + ".SPEED");
                    cellObj.childNodes[0].nodeValue=speed;
                    cellObj = document.getElementById(filename + ".ETA");
                    cellObj.childNodes[0].nodeValue=eta;
                }
                    
            }
            RemoveRows(filelist);
        } else {
            alert('There was a problem with the request.');
        }
    }
}
    

    
    
