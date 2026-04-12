class CombatUI{
    constructor(parent){
        this.element = null;
        this.entities = {};
        this.active_entity = null;
        this.active_ui = null;
        this.parent = parent;
        this.available_actions = {};
        this.radials = {
            main: new Radial(
                {inner: 150, outer: 250},
                [
                    {
                        name: "Test1",
                        click: ()=>{
                            let entity = this.entities[this.active_entity];
                            entity.target = 152;
                            window.GameEventBus.trigger(
                                "PlayerCombatantCommand",
                                {
                                    eid: this.active_entity,
                                    action: "Strike",
                                    target: entity.target
                                }
                            );
                            this.element.hidden = true;
                        }
                    },
                    {
                        name: "Test2",
                        click: ()=>{console.log(1);}
                    },
                    {
                        name: "Test3",
                        click: ()=>{}
                    }
                ],
                {"--color-fill": "rgba(0,0,255,0.5)", "--color-hover": "rgba(255,0,0,1)", "--opacity": "60%"}
            )
        }
        window.GameEventBus.on("CombatUpdate", this.onTickUpdate.bind(this));
        window.GameEventBus.on("CombatReadyEntity", this.setReadyEntity.bind(this));
        document.addEventListener("gamepad", this.gamePadEvent.bind(this))
    }
    render(hide=false){
        if(this.element!= null){
            this.element.remove();
            this.element = null;
        }
        this.element = this.parent.appendChild(document.createRange().createContextualFragment(`
            <div class="combat-ui"></div>                
        `).firstElementChild);
        let outer_this = this;
        if(this.active_ui){
            this.active_ui.render(this.element, this.entities[this.active_entity].pos);
        }
        
        if(hide){
            this.element.hidden = true;
        }

        return this.element;
    }
    gamePadEvent(event){
        if("B" in event.detail && !event.detail.B && this.active_ui){
            console.log(this.active_ui.previous)
            this.setActiveRadial(this.active_ui.previous);
        }
    }
    setActiveRadial(radial){
        if(radial in this.radials){
            this.active_ui.destroy();
            this.active_ui = this.radials[radial];
            this.render();
        }
    }
    setReadyEntity(data){
        this.active_entity = Number(data.eid);
        this.available_actions = data.actions;
        //this.active_ui = this.radials.main;
        for(const [name, radial] of Object.entries(this.radials)){
            radial.destroy();
        }
        this.radials = {};
        let root = this;
        function navigate(node, details, previous){
            let options = [];
            for(const [sub_node, sub_details] of Object.entries(details)){
                if(sub_details.type == "tree"){
                    options.push({
                        name: sub_node,
                        click: ()=>{
                            root.setActiveRadial(sub_node);
                        }
                    });
                    navigate(sub_node, sub_details.nodes, node);
                }else if(sub_details.type == "action"){
                    options.push({
                        name: sub_node,
                        click: ()=>{
                            let entity = root.entities[root.active_entity];
                            entity.target = 152;
                            window.GameEventBus.trigger(
                                "PlayerCombatantCommand",
                                {
                                    eid: root.active_entity,
                                    action: sub_node,
                                    target: entity.target
                                }
                            );
                            root.element.hidden = true;
                        }
                    });
                }
            }
            root.radials[node] = new Radial({inner: 150, outer: 250}, options, previous)
        }
        navigate("main", data.actions.nodes, "main")
        console.log(JSON.stringify(this.radials));
        this.active_ui = this.radials["main"];
        this.render(false);
    }
    onTickUpdate(data){
        this.entities = {};
        for(const [eid, details] of Object.entries(data.entities)){
            this.entities[Number(eid)] = details;
            if(this.active_ui && this.active_entity){
                this.active_ui.position(this.entities[this.active_entity].pos);
            }
        }
    }
}