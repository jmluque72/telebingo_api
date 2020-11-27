String.prototype.title = function() {
    return this.charAt(0).toUpperCase() + this.slice(1);
}


String.prototype.join = function(arr) {
    if(arr.length == 0)
        return "";
    if(arr.length == 1)
        return arr[0];
    var joined = arr[0];
    for(var idx=1; idx < arr.length; idx++)
        joined += this + arr[idx];
    return joined;
}
