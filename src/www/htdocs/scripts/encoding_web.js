if (document.images){
  var parselimit=2
}


function beginrefresh(){
  if (!document.images)
     return
     
  cellObj = document.getElementById("refresh");
  if (parselimit==1) {
       
       cellObj.childNodes[0].nodeValue="Updating";
       parselimit=10
       makeRequest('encoding_web.rpy?cmd=encodingstatus','EncodingStatus');
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

    if (request_type == 'EncodingStatus')
        httpRequest.onreadystatechange = function() { UpdateEncodingStatus(httpRequest); };
    if (request_type == 'UpdateBurnList')
        httpRequest.onreadystatechange = function() { UpdateBurnFileList(httpRequest); };
    if (request_type == 'changedirectory')
        httpRequest.onreadystatechange = function() { UpdateFileList(httpRequest); };
    httpRequest.open('GET', url, true);
    httpRequest.send('');

}

function EncodeFile(file_name) {
    var url;
    
    url = 'encoding_web.rpy?encodefile=' + file_name
    url = url + '&preset=' + document.getElementById('profile').value
    makeRequest(url,'EncodingStatus');
}


function DisplayAdvancedOptions() {
    var list;

    list = document.getElementById('AdvancedOptionsList')

    if (list.style.display == "")  {
        list.style.display = "none";
    }
    else {
       list.style.display = "";
    }
}

function UpdateEncodingStatus(httpRequest) {
    var j,cellObj,nodls;
    var cfile,filename,percent,amtdone,filesize,speed,eta;

    nodls = true;
    if (httpRequest.readyState == 4) {
        if (httpRequest.status == 200) {
                
                // Check to see if a table row exists for the file.
                cellObj = document.getElementById('EncodingStatus');
                cellObj.innerHTML = httpRequest.responseText 
                                
        } else {
            alert('There was a problem with the request.');
        }
    }
}



function UpdateFileList(httpRequest) {
    var cellObj,nodls;
   
    nodls = true;
    if (httpRequest.readyState == 4) {
        if (httpRequest.status == 200) {
                
                // Check to see if a table row exists for the file.
                cellObj = document.getElementById('FileList');
                cellObj.innerHTML = httpRequest.responseText 
                                
        } else {
            alert('There was a problem with the request.');
        }
    }
}



function ChangeDirectory(filename) {
    url_filename= Url.encode(filename)
    makeRequest('encoding_web.rpy?browsefolder=' + url_filename,'changedirectory')
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
