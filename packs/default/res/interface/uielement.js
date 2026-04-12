class UIElement{
    constructor(){
        this.element = null;
        this.controller = new AbortController();
    }
    render(parent_element, offset){ /* do nothing */ }
    position(offset){ /* do nothing */}
    destroy(){
        if(this.element!=null){
            this.element.remove();
            this.element = null;
            this.controller.abort();
            this.controller = new AbortController();
        }
    }
}