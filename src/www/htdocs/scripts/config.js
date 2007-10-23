
function PrepareFileList(cname) {
    var cvalue,tblabel,tbfile,cnt;

    cvalue = ""
    tblabel = document.getElementById(cname + "_label0")
    tbfile = document.getElementById(cname + "_file0")

    cnt = 0
    while (tblabel != null ) {
        if (tblabel.value != "") {
            if (tbfile != null)
                cvalue = cvalue + "('" +  tblabel.value  + "','" + tbfile.value + "'),";
            else
                cvalue = cvalue + "'" + tblabel.value + "',"
        }
        cnt++;
        tblabel = document.getElementById(cname + "_label"+cnt)
        tbfile = document.getElementById(cname + "_file"+cnt)
    }
    
    cvalue = "[" + cvalue.substring(0,cvalue.length -1) + "]";
    return cvalue;
}

function ShowList(cname) {
    var list;

    list = document.getElementById(cname)
    if (list.style.display == "") 
	list.style.display = "none";
    else
       list.style.display = "";
}

function MoveTVChannel(cname,crow,cmove) {
    var tvalue,svalue,dvalue,drow;
    
    drow = crow + cmove
    dvalue = document.getElementById("TV_CHANNELS_item" + drow)
    if (dvalue == null) 
        return
    
    tvalue = dvalue.value
    dvalue.value = document.getElementById("TV_CHANNELS_item" + crow).value 
    document.getElementById("TV_CHANNELS_item" + crow).value = tvalue    
    document.getElementById(cname + "_btn_update").style.display = ""

}

function PrepareChannelList(cname) {
    cvalue = "["
    tblabel = document.getElementById("TV_CHANNELS_item0")
    cnt = 0
    while (tblabel != null ) {
        if (tblabel.value != "")
            cvalue = cvalue + "" +  tblabel.value  + ",";
        cnt++;
        tblabel = document.getElementById("TV_CHANNELS_item" + cnt )
    }
    
    cvalue =  cvalue.substring(0,cvalue.length -1) + "]";
    return cvalue;
}

function PrepareItemList(cname) {
    var rcnt,ccnt,cvalue,tblcell,start_char,end_char;
    var cline,curcell, column_cnt, tb_value;
    
    cvalue = ""
    tblcell = document.getElementById(cname + "_item00")
    rcnt = 0
    
    // Loop throught all of the rows.
    while (tblcell != null ) {
        // Loop throught all of the cols
        ccnt = 0
        cline = ""
        column_cnt = 0
        while (tblcell != null) {
            if (tblcell.value != "")
                start_char = "'"
                end_char = "'"
                schar = tblcell.value.charAt(0);
                echar = tblcell.value.charAt(tblcell.value.length - 1)
                if (schar == "(")
                    start_char = "";
                if (echar == ")")
                    end_char = "";

                tb_value = tblcell.value;
                curcell = start_char +  tb_value + end_char
                if (curcell != "''") {
                    cline =  cline + curcell + ",";
                    column_cnt++;
                }
                ccnt++;
            tblcell = document.getElementById(cname + "_item" + rcnt + ccnt)
        }
        rcnt++;
        ccnt = 0
        if (column_cnt > 0)
            cvalue = cvalue + '(' + cline.substring(0,cline.length -1) + '),';
        tblcell = document.getElementById(cname + "_item" + rcnt + ccnt);
    }
        
    if (cvalue != "") 
        cvalue = "[" + cvalue.substring(0,cvalue.length -1) + "]";

    return cvalue;
}


function UpdateStatus(hRequest,cname,cstatus) {
    var cell,btnUpdate,disableupdate;

    if (hRequest.readyState == 4) {
        if (hRequest.status == 200) {
           cell = document.getElementById(cstatus);
           cell.innerHTML = hRequest.responseText;
            
            btnUpdate =  document.getElementById(cname + "_btn_update") 
            
            if (cell.textContent.search("Error") == -1)
               btnUpdate.style.display = ""; 
            else
               btnUpdate.style.display = "none";

        } else {
            alert('There was a problem with the request.');
        }
    }
}

function makeRequest(url,cname,cstatus) {
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
    httpRequest.onreadystatechange = function() { UpdateStatus(httpRequest,cname,cstatus); };
    httpRequest.open('GET', url, true);
    httpRequest.send('');
}

function SaveValue(control_name,type) {
    // Get the Value from the text box. 
    var svalue,tb,chk,updateurl,strenable;
    var startline,endline, sname,div_enable;
    var other_opts;

    other_opts = ''
    sname = document.getElementById(control_name + '_ctrlname').value
    
    if (type == "tv_channels") 
        svalue = PrepareChannelList(control_name);
    else if (type == "fileitemlist")
        svalue =  PrepareFileList(control_name);
    else if (type == "itemlist")
        svalue = PrepareItemList(control_name);
    else if(type == 'keymap') {
        other_opts = '&syntaxcheck=FALSE'
        sname = 'KEYMAP[' + document.getElementById( control_name + '_key').value + ']'
        svalue = document.getElementById(control_name + '_event').value
    }
    else {
        tb = document.getElementById(control_name);
        svalue = tb.value;
    }
    
    chk  = document.getElementById(control_name + "_chk")
    startline = document.getElementById(control_name + "_startline").value
    endline = document.getElementById(control_name + "_endline").value
    div_enable = document.getElementById(control_name + '_enable')
    
    if (chk.checked) { 
        strenable = "TRUE";
        div_enable.className = 'enablecontrol'
    } 
    else {
        strenable = "FALSE"        
        div_enable.className = 'disablecontrol'
    }
    
    configfile =document.getElementById('configfile').value
    updateurl = 'configedit.rpy?configfile=' + configfile + '&cmd=UPDATE&udname=' + sname + '&udvalue=' + svalue + '&udenable=' + strenable;
    updateurl = updateurl + "&startline=" + startline + '&endline=' + endline + other_opts;
   
   makeRequest(updateurl,control_name,control_name + "_fileline");
}

function CheckValue(control_name ,type,row) {
    var svalue,tb,chk,updateurl,strenable;
    
    sname = document.getElementById(control_name + '_ctrlname').value
    if (type == "tv_channels") 
        svalue = PrepareChannelList(control_name);
    
    else if (type == "fileitemlist") 
        svalue =  PrepareFileList(control_name);
    
    else if (type == "itemlist") 
        svalue = PrepareItemList(control_name);

    else if(type == 'keymap') {
        document.getElementById(control_name + '_btn_update').style.display = ''
        
        sname = 'KEYMAP[' + document.getElementById( control_name + '_key').value + ']'
        svalue = document.getElementById(control_name + '_event').value
    }
    else {
        tb = document.getElementById(control_name);
        svalue = tb.value;
    }
    
    //alert(svalue);
    configfile =document.getElementById('configfile')
    updateurl = 'configedit.rpy?configfile=' + configfile + '&cmd=CHECK&udname=' + sname + '&udvalue=' + svalue
    if (type != 'keymap') 
        makeRequest(updateurl,control_name,control_name + "_check");
}


function DeleteLines(cname, sline,eline) {
     var url;   

    configfile =document.getElementById('configfile')
    url = 'configedit.rpy?configfile=' + configfile + '&cmd=DELETE&startline=' + sline + '&endline=' + eline
    makeRequest(url,cname,cname + "_list")

}
