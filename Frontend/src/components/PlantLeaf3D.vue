<script setup>
import { TresCanvas } from '@tresjs/core'
// Cientos removed temporarily for stability
</script>

<template>
  <div class="canvas-container">
    <TresCanvas alpha>
      <TresPerspectiveCamera :position="[0, 2, 7]" :look-at="[0,0,0]" />
      
      <TresMesh :position="[0, 0, 0]">
        <TresIcosahedronGeometry :args="[2, 2]" />
        <TresMeshStandardMaterial 
          color="#4caf50" 
          :wireframe="true" 
          emissive="#1b5e20"
        />
      </TresMesh>

      <TresMesh :position="[0, 0, 0]" :rotation="[Math.PI / 2, 0, 0]">
        <TresTorusGeometry :args="[3, 0.01, 16, 100]" />
        <TresMeshStandardMaterial color="#ffca28" />
      </TresMesh>
      
      <TresAmbientLight :intensity="1" />
      <TresDirectionalLight :position="[5, 5, 5]" :intensity="2" />
    </TresCanvas>
  </div>
</template>

<style scoped>
.canvas-container {
  width: 100%;
  height: 600px;
  position: absolute;
  top: 0;
  right: -100px;
  z-index: 1;
  pointer-events: none;
}
</style>
