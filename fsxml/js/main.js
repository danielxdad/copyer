var FS_XML;

function readSyncXMLFile(file){
    var xhr = new XMLHttpRequest(),
        urlblob = URL.createObjectURL(file);
    
    f = file;
    xhr.open('GET', urlblob, async = false);
    xhr.send();
    xhr.overrideMimeType('text/xml');
    //console.log(xhr.response.length);
    return xhr.responseXML;
}

function getFileInput(){
    var fileElement = document.getElementById('fsxml_file');

    if (fileElement.files.length > 0)
        return fileElement.files[0];
    
    return undefined;
}

function unquote(data){
    var re = /%[0-9abcdef]{2}/gi;
    var matchs = data.match(re);

    if (matchs !== null){
        matchs.forEach(function(e, i){
            var c = String.fromCharCode(parseInt(e.substr(1), 16));
            data=data.replace(e,c);
        })
    }
    return data;
}

function getXPathForElement(el, xml) {
	var xpath = '';
	var pos, tempitem2;
	
	while(el !== xml.documentElement) {		
		pos = 0;
		tempitem2 = el;
		while(tempitem2) {
			if (tempitem2.nodeType === 1 && tempitem2.nodeName === el.nodeName) { // If it is ELEMENT_NODE of the same name
				pos += 1;
			}
			tempitem2 = tempitem2.previousSibling;
		}
		
		//xpath = "*[name()='"+el.nodeName+"' and namespace-uri()='"+(el.namespaceURI===null?'':el.namespaceURI)+"']["+pos+']'+'/'+xpath;
		xpath = "*[name()='"+el.nodeName+"']["+pos+']'+'/'+xpath;

		el = el.parentNode;
	}
	xpath = '/*'+"[name()='"+xml.documentElement.nodeName+"']"+'/'+xpath;
	xpath = xpath.replace(/\/$/, '');
	return xpath;
}

function humanizeSize(size){
    var i=0, suffixs = ['B', 'KB', 'MB', 'GB', 'TB'];
        
    size = parseFloat(size, 10);
    while(parseInt(size/1024, 10) > 0){
        size /= 1024;
        i+=1;
    }
    return size.toFixed(2) + ' ' + suffixs[i];
}

function onclick_dir(event){
    var target = event.target,
        dirNode = FS_XML.getElementById((target.parentNode || target.elementNode).id),
        activeDir = $('.item-folder-active');
	
    if ( activeDir[0] != this ){
        activeDir.removeClass('item-folder-active');
        $(target).addClass('item-folder-active');
        lsDir(dirNode);
    }
    else{
        activeDir.parent().children('li').slice(1).slideToggle('fast');
    }
}

function onclick_file(event){
    var target = event.target,
        fileNode = FS_XML.getElementById(target.id),
        atime = new Date($(fileNode).attr('atime')).toLocaleString(),
        ctime = new Date($(fileNode).attr('ctime')).toLocaleString(),
        mtime = new Date($(fileNode).attr('mtime')).toLocaleString(),
        size = $(fileNode).attr('size'),
        infoFile = $('#info_file_selected');
        
        $('#root_file_list > li.item-file-active').removeClass('item-file-active');
        $(target).addClass('item-file-active');
        
        infoFile.html('Size: ' + humanizeSize(size) + ' | CTime: ' + ctime + ' | MTime: ' + mtime + ' | ATime: ' + atime);
}

function lsDir(dirNode){
    var tagNode = dirNode.tagName || dirNode.nodeName || dirNode.localName;
    var has_childs, el_name, ulNode, subNode, ulSubNode;
    
    $('#info_file_selected').html('');
    if ( tagNode === 'dir' ){
        //has_childs = dirNode.childNodes.length > 0;
        ulNode = $('#' + dirNode.id);
        if( ulNode.length == 0){
            if ( typeof dirNode.firstChild.data !== 'undefined'){
                el_name = unquote(dirNode.firstChild.data);
                
                if (el_name.length == 2 && el_name.search(/[A-Z]:{1}/g) === 0){
                    ulNode = $('<ul id="' + dirNode.id +'" class="drive"><li>' + el_name + '</li></ul>');
                }
                else{
                    ulNode = $('<ul id="' + dirNode.id + '" class="dir"><li>' + el_name + '</li></ul>');
                }
                ulNode.children('li').click(onclick_dir);
                ulNode.appendTo('#root_folder_list');
            }
        }
        
        //Subdirs & Files
        $('#root_file_list > li').remove();
        for(var i=0; i<= dirNode.childNodes.length-1; i++){
            tagName =  dirNode.childNodes[i].tagName || dirNode.childNodes[i].nodeName || dirNode.childNodes[i].localName;
            subNode = dirNode.childNodes[i];
            
            if ( tagName === 'dir'){
                if ( typeof subNode.firstChild.data !== 'undefined' && $('#' + subNode.id).length == 0){
                    el_name = unquote(subNode.firstChild.data);
                    ulSubNode=$('<li><ul id="' + subNode.id + '" class="dir"><li>' + el_name + '</li></ul></li>');
                    ulSubNode.css({'display': 'none'});
                    ulSubNode.children('ul').children('li').click(onclick_dir);
                    ulSubNode.appendTo(ulNode);
                    ulSubNode.slideDown('fast');
                }
            }
            else if ( tagName === 'file' ){
                if ( typeof subNode.firstChild.data !== 'undefined'){
                    el_name = unquote(subNode.firstChild.data);
                    ulSubNode = $('<li id="' + subNode.id + '">' + el_name + '</li>');
                    ulSubNode.click(onclick_file);
                    ulSubNode.appendTo('#root_file_list');
                }
            }
        }
    }
}

function showTree(nodePath/*rootNode*/){
    var iterator = FS_XML.evaluate(nodePath, FS_XML, null, XPathResult.UNORDERED_NODE_ITERATOR_TYPE, null );

    try {
        var thisNode = iterator.iterateNext();

        while (thisNode) {
            lsDir(thisNode);
            thisNode = iterator.iterateNext();
        }
    }
    catch (e) {
        console.log( 'Error XPath iterator: ' + e );
    }
}

function showFSXMLFileInfo(file){
    console.log('FSXML file: ' + file.name + ' | Size: ' + file.size + ' | Last modified date: ' + file.lastModifiedDate.toLocaleString());
    $('#info_fsxml_file').html('FSXML file: ' + file.name + ' | Size: ' + humanizeSize(file.size) + ' | Last modified date: ' + file.lastModifiedDate.toLocaleString());
}
            
function mount_click(event){
    var file = getFileInput(), blob, root, drives;
    
    if ( typeof file === 'undefined' ) {
        $('#fsxml_file').click();
        return;
    }
    $('#root_folder_list > li').remove();
    showFSXMLFileInfo(file);
    
    FS_XML = undefined;
    FS_XML = readSyncXMLFile(file);
    
    root = $(FS_XML).children('root');
    if ( ! root.length )
        throw Error('Invalid FSXML file');
    if (root.length != 1)
        throw Error('Invalid FSXML file');
    root = root[0];
        
    showTree(getXPathForElement(root, FS_XML) + '/dir');
    this.disabled = true;
}

function on_click_fsxml_file(event){
    if ( this.files.length > 0)
        $('#mount').click();
}

$(function(){
    $('#mount').click(mount_click);
    $('#fsxml_file').change(on_click_fsxml_file)
});
