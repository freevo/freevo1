if (document.images){
  var parselimit=2
}

function beginrefresh(){
  if (!document.images)
     return
     
  cellObj = document.getElementById("refresh");
  if (parselimit==1) {
       
       cellObj.childNodes[0].nodeValue="Updating";
       parselimit=60
       makeRequest('youtube.rpy?xml=1');
       setTimeout("beginrefresh()",1000)
  }
  else{ 
     parselimit-=1
     cellObj.childNodes[0].nodeValue="Refresh In : " + parselimit;
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
    httpRequest.onreadystatechange = function() { UpdateTable(httpRequest); };
    httpRequest.open('GET', url, true);
    httpRequest.send('');

}

function TableAddRow(file,filesize,percent,amtdone,speed,eta) {
    var tbl,lastrow,newrow,cellLeft;
    var textNode;

    var pickLink,pickText

    tbl = document.getElementById("filelist")
    lastrow = tbl.rows.length;
    newrow = tbl.insertRow(lastrow);
    newrow.id = file
    newrow.className = "chanrow"

    cellLeft = newrow.insertCell(0);
    delLink=document.createElement('a');
    pickText=document.createTextNode('delete');
    delLink.appendChild(pickText);
    delLink.setAttribute('href','youtube.rpy?Delete=1&file=' + file);
    cellLeft.appendChild(delLink);
    cellLeft.className = "basic"

    cellLeft = newrow.insertCell(1);
    delLink=document.createElement('a');
    pickText=document.createTextNode(file);
    delLink.appendChild(pickText);
    delLink.setAttribute('href','youtube.rpy?playfile=' + file);
    cellLeft.appendChild(delLink);
    cellLeft.className = "basic"

//    cellLeft = newrow.insertCell(1);
//    textNode = document.createTextNode(file);
//    cellLeft.appendChild(textNode);
//    cellLeft.className = "basic"

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
        }
        cnt = 0;
    }
}

function UpdateCell(cellname,value) {
    var cellObj;

    cellObj = document.getElementById(cellname);
    cellObj.childNodes[0].nodeValue=value;
}

function UpdateTable(httpRequest) {
    var j,cellObj,nodls;
    var cfile,filename,percent,amtdone,filesize,speed,eta;

    nodls = true;
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
                if (amtdone != "done") {
                    parselimit = 10;
                }

                // Check to see if a table row exists for the file.
                cellObj = document.getElementById(filename);
                if (cellObj == null) {
                    TableAddRow(filename,filesize,percent,amtdone,speed,eta)
                }
                else {
                    UpdateCell(filename + ".FILESIZE",filesize)
                    UpdateCell(filename + ".PERCENT",percent)
                    UpdateCell(filename + ".SOFAR",amtdone)
                    UpdateCell(filename + ".SPEED",speed)
                    UpdateCell(filename + ".ETA",eta)
                }                
            }
            RemoveRows(filelist);
        } else {
            alert('There was a problem with the request.');
        }
    }
}
    

    
    
