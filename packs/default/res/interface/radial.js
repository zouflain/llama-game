class Radial extends UIElement{
    constructor(circle, options = null, styles = null){
        super();
        this.options = options ?? {};
        this.circle = circle;
        this.styles = styles ?? {};
    }
    render(parent_element, screen_pos){
        if(this.element!=null){
            this.element.remove();
            this.element = null;
        }
        this.element = parent_element.appendChild(document.createRange().createContextualFragment(`
            <div class="svg-container"></div>
        `).firstElementChild);
        Object.assign(this.element.style, {
            width: (this.circle.outer*2)+"px",
            height: (this.circle.outer*2)+"px",
            left: (screen_pos.x - this.circle.outer)+"px",
            top: (screen_pos.y - this.circle.outer)+"px"
        });
        for(const [prop, value] of Object.entries(this.styles)){
            this.element.style.setProperty(prop, value);
        }
        let gap_width = 8;
        let svgs = [];

        if(this.options.length > 0){
            let angle_step = 2*Math.PI/this.options.length;
            let angle_start = -Math.PI/2;
            for(const [i, option] of this.options.entries()){
                let svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
                svg.setAttribute("viewBox", `0, 0, ${this.circle.outer*2}, ${this.circle.outer*2}`)
                let angle_base = angle_start + angle_step*i;

                let adjusted = {
                    outer: Math.sqrt(Math.pow(this.circle.outer, 2) - Math.pow(gap_width/2, 2)),
                    inner: Math.sqrt(Math.pow(this.circle.inner, 2) - Math.pow(gap_width/2, 2))
                }
                let positions = [
                    {x: this.circle.outer-Math.sin(angle_base-angle_step/2)*gap_width/2+Math.cos(angle_base-angle_step/2)*adjusted.outer, y: this.circle.outer+Math.cos(angle_base-angle_step/2)*gap_width/2+Math.sin(angle_base-angle_step/2)*adjusted.outer},
                    {x: this.circle.outer+Math.sin(angle_base+angle_step/2)*gap_width/2+Math.cos(angle_base+angle_step/2)*adjusted.outer, y: this.circle.outer-Math.cos(angle_base+angle_step/2)*gap_width/2+Math.sin(angle_base+angle_step/2)*adjusted.outer},
                    {x: this.circle.outer+Math.sin(angle_base+angle_step/2)*gap_width/2+Math.cos(angle_base+angle_step/2)*adjusted.inner, y: this.circle.outer-Math.cos(angle_base+angle_step/2)*gap_width/2+Math.sin(angle_base+angle_step/2)*adjusted.inner},
                    {x: this.circle.outer-Math.sin(angle_base-angle_step/2)*gap_width/2+Math.cos(angle_base-angle_step/2)*adjusted.inner, y: this.circle.outer+Math.cos(angle_base-angle_step/2)*gap_width/2+Math.sin(angle_base-angle_step/2)*adjusted.inner}
                ];
                let commands = [
                    "M", positions[0].x, positions[0].y,
                    "A", this.circle.outer, this.circle.outer, 0, Number(angle_step > Math.PI), 1, positions[1].x,  positions[1].y,
                    "L", positions[2].x, positions[2].y,
                    "A", this.circle.inner, this.circle.inner, 0, Number(angle_step > Math.PI), 0, positions[3].x, positions[3].y,
                    "Z"
                ].join(" ");
                let path = document.createElementNS("http://www.w3.org/2000/svg", "path");
                path.setAttribute("d", commands);
                svg.appendChild(path);
                svg.addEventListener("click", option.click);
                svg.addEventListener("mouseenter", option.hover || this.defaultHover);
                svgs.push(svg);
            }
        }
        for(const svg of svgs){
            this.element.appendChild(svg);
        }
    }
    position(offset){
        Object.assign(this.element.style, {
            left: (offset.x - this.circle.outer)+"px",
            top: (offset.y - this.circle.outer)+"px"
        });
    }
    defaultHover(){
        window.GameEventBus.trigger(
            "AudioTrigger",
            {
                fmod_event: "event:/sword_hit"
            }
        )
    }
}