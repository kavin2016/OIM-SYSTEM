export default {
  name: 'EnableUserTreeNode',
  props: {
    node: { type: Object, required: true },
    level: { type: Number, default: 0 },
    selectedId: { type: [Number, String], default: '' },
  },
  emits: ['select'],
  computed: {
    isUser() {
      return this.node.type === 'user'
    },
    isSelected() {
      return this.isUser && Number(this.selectedId) === Number(this.node.id)
    },
  },
}
