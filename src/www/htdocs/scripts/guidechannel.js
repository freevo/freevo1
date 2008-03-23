
function ShowList(cname) {
    var list, anchor;

    list = document.getElementById(cname )

    if (list.style.display == "")  {
        list.style.display = "none";
    }
    else {
       list.style.display = "";
    }
}


function ChangeChannel(control) {
    var url;

    url = 'guidechannel.rpy?getprogramlist=' + control.value
    makeRequest(url)
}

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
    httpRequest.onreadystatechange = function() { UpdateChannel(httpRequest); };
    httpRequest.open('GET', url, true);
    httpRequest.send('');

}


function UpdateChannel(httpRequest) {
    var programlist;
    
    if (httpRequest.readyState == 4) {
        if (httpRequest.status == 200) {
            programlist = document.getElementById("ProgramList");
            programlist.innerHTML = httpRequest.responseText;
         } else {
            alert('There was a problem with the request.');
        }
    }
}
    

    
    
