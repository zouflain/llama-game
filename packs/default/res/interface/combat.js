class CombatUI{
    constructor(parent){
        this.element = null;
        this.entities = {};
        this.active_entity = null;
        this.active_ui = null;
        this.parent = parent;
        this.postures = {};
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
                                    posture: entity.posture,
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
        window.GameEventBus.on("CombatInit", this.init.bind(this));
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
    init(data){
        this.postures = data.postures;
    }
    setReadyEntity(data){
        this.active_entity = Number(data.eid);
        this.active_ui = this.radials.main;
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