/**
 * This class manages the exhaust and smoke effects for a scene. It initializes the materials and VFX components for the exhausts and smokes, and provides methods to control their states.
 *
 */
@component
export class ExhaustControls extends BaseScriptComponent {
  @input
  exhausts: SceneObject[] = []

  @input
  smokes: SceneObject[] = []

  private exhaustFireMaterials: Material[] = []
  private exhaustGlowMaterials: Material[] = []
  private smokeVFXs: VFXComponent[] = []

  onAwake(): void {
    this.initExhaustMaterials()
    this.initSmokeVFXs()
    this.turnOffExhausts()
    this.turnOffSmokes()
  }

  initExhaustMaterials = (): void => {
    for (let i = 0; i < this.exhausts.length; i++) {
      const fireChild = this.exhausts[i].getChild(0)
      const fireRenderMesh = fireChild ? fireChild.getComponent("RenderMeshVisual") : null
      if (fireRenderMesh && fireRenderMesh.mainMaterial) {
        this.exhaustFireMaterials.push(fireRenderMesh.mainMaterial)
      } else {
        this.exhaustFireMaterials.push(null)
      }

      const glowChild = fireChild ? fireChild.getChild(0) : null
      const glowRenderMesh = glowChild ? glowChild.getComponent("RenderMeshVisual") : null
      if (glowRenderMesh && glowRenderMesh.mainMaterial) {
        this.exhaustGlowMaterials.push(glowRenderMesh.mainMaterial)
      } else {
        this.exhaustGlowMaterials.push(null)
      }
    }
  }

  initSmokeVFXs = (): void => {
    for (let i = 0; i < this.smokes.length; i++) {
      const vfxComponent = this.smokes[i].getComponent("Component.VFXComponent")
      if (vfxComponent) {
        this.smokeVFXs.push(vfxComponent)
      }
    }
  }

  engineReady = (): void => {
    if (!this.exhaustFireMaterials || !this.exhaustGlowMaterials) {
      print("Materials arrays not initialized properly")
      return
    }
    
    for (let i = 0; i < this.exhausts.length; i++) {
      try {
        if (this.exhausts[i]) {
          this.exhausts[i].enabled = true
        }
        if (i < this.exhaustFireMaterials.length && this.exhaustFireMaterials[i] && this.exhaustFireMaterials[i].mainPass) {
          this.exhaustFireMaterials[i].mainPass.fire_scale = 1.0
        }
        if (i < this.exhaustGlowMaterials.length && this.exhaustGlowMaterials[i] && this.exhaustGlowMaterials[i].mainPass) {
          this.exhaustGlowMaterials[i].mainPass.glow_scale = 1.0
        }
      } catch (error) {
        print(`Error in engineReady at index ${i}: ${error}`)
        print(`exhaustFireMaterials[${i}]: ${this.exhaustFireMaterials[i]}`)
        print(`exhaustGlowMaterials[${i}]: ${this.exhaustGlowMaterials[i]}`)
      }
    }
  }

  turnOnExhausts = (): void => {
    for (let i = 0; i < this.exhausts.length; i++) {
      if (this.exhausts[i]) {
        this.exhausts[i].enabled = true
      }
      if (this.exhaustFireMaterials[i] && this.exhaustFireMaterials[i].mainPass) {
        this.exhaustFireMaterials[i].mainPass.fire_scale = 0.15
      }
      if (this.exhaustGlowMaterials[i] && this.exhaustGlowMaterials[i].mainPass) {
        this.exhaustGlowMaterials[i].mainPass.glow_scale = 0.15
      }
    }
  }

  turnOffExhausts = (): void => {
    for (let i = 0; i < this.exhausts.length; i++) {
      if (this.exhausts[i]) {
        this.exhausts[i].enabled = false
      }
      if (this.exhaustFireMaterials[i] && this.exhaustFireMaterials[i].mainPass) {
        this.exhaustFireMaterials[i].mainPass.fire_scale = 0.0
      }
      if (this.exhaustGlowMaterials[i] && this.exhaustGlowMaterials[i].mainPass) {
        this.exhaustGlowMaterials[i].mainPass.glow_scale = 0.0
      }
    }
  }

  turnOnSmokes = (): void => {
    for (let i = 0; i < this.smokes.length; i++) {
      this.smokes[i].enabled = true
    }
  }

  turnOffSmokes = (): void => {
    for (let i = 0; i < this.smokes.length; i++) {
      this.smokes[i].enabled = false
    }
  }

  setEngineSmokesValue = (value: any): void => {
    for (let i = 0; i < this.smokes.length; i++) {
      if (this.smokeVFXs[i] && this.smokeVFXs[i].asset) {
        const particles: any = this.smokeVFXs[i].asset.properties
        particles["particlesReduce"] = value
      }
    }
  }
}
