class UIElement{
    constructor(){
        this.element = null;
    }
    render(parent_element, offset){ /* do nothing */ }
    position(offset){ /* do nothing */}
    destroy(){
        if(this.element!=null){
            this.element.remove();
            this.element = null;
        }
    }
}