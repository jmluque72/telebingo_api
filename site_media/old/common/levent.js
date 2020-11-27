
var LEvent = function(name, variables){

    this.name = name;
    this.variables = variables;
    this.listeners = [];

}

LEvent.prototype.addListener = function(fnc) {
    this.listeners.push(fnc);
}

LEvent.prototype.emit = function(values){
    for(var idx=0; idx < this.variables.length; idx++){
        var vname = this.variables[idx];
        if(!values.hasOwnProperty(vname))
            throw "variable '" + vname + "' not found";
    }
    for(var idx=0; idx < this.listeners.length; idx++)
        this.listeners[idx](values);
}
