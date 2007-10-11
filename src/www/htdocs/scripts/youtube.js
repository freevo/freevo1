if (document.images){
  var parselimit=2
}

function StartDownload() {
    var url,file_url,download_type;
    
    file_url = Url.encode(document.getElementById('dl_url').value);
    download_type = document.getElementById('download_type').value;
    if (file_url != "") {
        url = "youtube.rpy?xml=1&dlscript=" + download_type + "&dl_url=" + file_url;
        makeRequest(url,'file_list'); 
        document.getElementById('dl_url').value = ""
        parselimit=3
    }
}

function PlayFile(flv_file) {
    var url;
    
    url = 'youtube.rpy?cmd=Play&playfile=' + flv_file ;
    makeRequest(url,'flowplayer');
}
function PlayFileOld(flv_file) {
    var divflowplayer,flowplayer,clip,setA;
   
    divflowplayer = document.getElementById('flowplayerholder')
    divflowplayer.style.display = ""
    clip = {name: 'flv_file' , url: 'youtube/' + flv_file }

    flowplayer = document.getElementById("FlowPlayer");
    flowplayer.videoFile = flv_file;
    flv_file = "/youtube/" + flv_file
    setA = {"url" : flv_file}
    this.fo.setAttribute(setA);

}


function beginrefresh(){
  if (!document.images)
     return
     
  cellObj = document.getElementById("refresh");
  if (parselimit==1) {
       
       cellObj.childNodes[0].nodeValue="Updating";
       parselimit=60
       makeRequest('youtube.rpy?xml=1','file_list');
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

function makeRequest(url , request_type) {
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

    if (request_type == "file_list") 
        httpRequest.onreadystatechange = function() { UpdateTable(httpRequest); };
    
    if (request_type == "flowplayer") 
        httpRequest.onreadystatechange = function() { UpdateFlowPlayer(httpRequest); };

    httpRequest.open('GET', url, true);
    httpRequest.send('');

}

function ConvertToFlv(media_file) {
    var answer,url;
    
    answer = confirm ("Covert File to flv ?" + media_file);
    if (answer)  {
       url = "youtube.rpy?xml=1&cmd=Convert&convert_file=" + media_file 
       makeRequest(url)
    }

}

function DeleteFile(delete_file) {
    var answer,url;
    
    answer = confirm ("Delete File ?" + delete_file);
    if (answer)  {
       url = "youtube.rpy?xml=1&cmd=Delete&delete_file=" + delete_file 
       makeRequest(url,file_list)
    }
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
    delLink.setAttribute('onclick','DeleteFile("' + file  + '")');
    cellLeft.appendChild(delLink);
    cellLeft.className = "basic"

    cellLeft = newrow.insertCell(1);
    delLink=document.createElement('a');
    pickText=document.createTextNode(file);
    delLink.appendChild(pickText);
    file_ext = file.substr(file.length - 3, file.length);
    if (file_ext == "flv") 
        //delLink.setAttribute('onclick','PlayFile("' + file + '")');
        delLink.setAttribute('href','youtube.rpy?playfile=' + file);
    else 
        delLink.setAttribute('onclick','ConvertToFlv("' + file + '")');

    cellLeft.appendChild(delLink);
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

function UpdateFlowPlayer(httpRequest) {
    var flowplayer_div;
    
    if (httpRequest.readyState == 4) {
        if (httpRequest.status == 200) {
            flowplayer_div = document.getElementById('flowplayer_div')
            flowplayer_div.innerHTML = httpRequest.responseText

        } else {
            alert('There was a problem with the request.');
        }
    }
}


/**
*
* URL encode / decode
* http://www.webtoolkit.info/
*
**/

var Url = {

    // public method for url encoding
    encode : function (string) {
        return escape(this._utf8_encode(string));
    },

    // public method for url decoding
    decode : function (string) {
        return this._utf8_decode(unescape(string));
    },

    // private method for UTF-8 encoding
    _utf8_encode : function (string) {
        string = string.replace(/\r\n/g,"\n");
        var utftext = "";

        for (var n = 0; n < string.length; n++) {

            var c = string.charCodeAt(n);

            if (c < 128) {
                utftext += String.fromCharCode(c);
            }
            else if((c > 127) && (c < 2048)) {
                utftext += String.fromCharCode((c >> 6) | 192);
                utftext += String.fromCharCode((c & 63) | 128);
            }
            else {
                utftext += String.fromCharCode((c >> 12) | 224);
                utftext += String.fromCharCode(((c >> 6) & 63) | 128);
                utftext += String.fromCharCode((c & 63) | 128);
            }

        }

        return utftext;
    },

    // private method for UTF-8 decoding
    _utf8_decode : function (utftext) {
        var string = "";
        var i = 0;
        var c = c1 = c2 = 0;

        while ( i < utftext.length ) {

            c = utftext.charCodeAt(i);

            if (c < 128) {
                string += String.fromCharCode(c);
                i++;
            }
            else if((c > 191) && (c < 224)) {
                c2 = utftext.charCodeAt(i+1);
                string += String.fromCharCode(((c & 31) << 6) | (c2 & 63));
                i += 2;
            }
            else {
                c2 = utftext.charCodeAt(i+1);
                c3 = utftext.charCodeAt(i+2);
                string += String.fromCharCode(((c & 15) << 12) | ((c2 & 63) << 6) | (c3 & 63));
                i += 3;
            }

        }

        return string;
    }

}
