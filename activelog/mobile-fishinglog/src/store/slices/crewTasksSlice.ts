import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { CrewMember, Task } from '@/types';

interface CrewTasksState {
  crew: CrewMember[];
  tasks: Task[];
  taskCategories: string[];
}

const initialState: CrewTasksState = {
  crew: [],
  tasks: [],
  taskCategories: [
    'maintenance',
    'safety',
    'navigation',
    'provisions',
    'cleaning',
    'equipment',
    'other'
  ],
};

const crewTasksSlice = createSlice({
  name: 'crewTasks',
  initialState,
  reducers: {
    addCrewMember: (state, action: PayloadAction<Omit<CrewMember, 'id'>>) => {
      const member: CrewMember = {
        id: `crew_${Date.now()}`,
        ...action.payload,
      };
      state.crew.push(member);
    },
    
    updateCrewMember: (state, action: PayloadAction<{ id: string; updates: Partial<CrewMember> }>) => {
      const { id, updates } = action.payload;
      const memberIndex = state.crew.findIndex(m => m.id === id);
      if (memberIndex !== -1) {
        state.crew[memberIndex] = { ...state.crew[memberIndex], ...updates };
      }
    },
    
    removeCrewMember: (state, action: PayloadAction<string>) => {
      const memberId = action.payload;
      state.crew = state.crew.filter(m => m.id !== memberId);
      
      // Unassign tasks from removed crew member
      state.tasks.forEach(task => {
        if (task.assignedTo === memberId) {
          task.assignedTo = undefined;
        }
      });
    },
    
    addTask: (state, action: PayloadAction<Omit<Task, 'id' | 'createdAt' | 'status'>>) => {
      const task: Task = {
        id: `task_${Date.now()}`,
        status: 'pending',
        createdAt: new Date(),
        ...action.payload,
      };
      state.tasks.push(task);
    },
    
    updateTask: (state, action: PayloadAction<{ id: string; updates: Partial<Task> }>) => {
      const { id, updates } = action.payload;
      const taskIndex = state.tasks.findIndex(t => t.id === id);
      if (taskIndex !== -1) {
        state.tasks[taskIndex] = { ...state.tasks[taskIndex], ...updates };
        
        // Set completion date if task is being marked as completed
        if (updates.status === 'completed' && state.tasks[taskIndex].completedAt === undefined) {
          state.tasks[taskIndex].completedAt = new Date();
        }
        
        // Update status to overdue if past due date
        if (state.tasks[taskIndex].dueDate && new Date() > new Date(state.tasks[taskIndex].dueDate!) && updates.status !== 'completed') {
          state.tasks[taskIndex].status = 'overdue';
        }
      }
    },
    
    assignTask: (state, action: PayloadAction<{ taskId: string; crewId: string }>) => {
      const { taskId, crewId } = action.payload;
      const taskIndex = state.tasks.findIndex(t => t.id === taskId);
      if (taskIndex !== -1) {
        state.tasks[taskIndex].assignedTo = crewId;
        if (state.tasks[taskIndex].status === 'pending') {
          state.tasks[taskIndex].status = 'in_progress';
        }
      }
    },
    
    unassignTask: (state, action: PayloadAction<string>) => {
      const taskId = action.payload;
      const taskIndex = state.tasks.findIndex(t => t.id === taskId);
      if (taskIndex !== -1) {
        state.tasks[taskIndex].assignedTo = undefined;
        if (state.tasks[taskIndex].status === 'in_progress') {
          state.tasks[taskIndex].status = 'pending';
        }
      }
    },
    
    completeTask: (state, action: PayloadAction<string>) => {
      const taskId = action.payload;
      const taskIndex = state.tasks.findIndex(t => t.id === taskId);
      if (taskIndex !== -1) {
        state.tasks[taskIndex].status = 'completed';
        state.tasks[taskIndex].completedAt = new Date();
      }
    },
    
    deleteTask: (state, action: PayloadAction<string>) => {
      state.tasks = state.tasks.filter(t => t.id !== action.payload);
    },
    
    addTaskCategory: (state, action: PayloadAction<string>) => {
      if (!state.taskCategories.includes(action.payload)) {
        state.taskCategories.push(action.payload);
        state.taskCategories.sort();
      }
    },
    
    updateOverdueTasks: (state) => {
      const now = new Date();
      state.tasks.forEach(task => {
        if (task.dueDate && new Date(task.dueDate) < now && task.status !== 'completed') {
          task.status = 'overdue';
        }
      });
    },
  },
});

export const {
  addCrewMember,
  updateCrewMember,
  removeCrewMember,
  addTask,
  updateTask,
  assignTask,
  unassignTask,
  completeTask,
  deleteTask,
  addTaskCategory,
  updateOverdueTasks,
} = crewTasksSlice.actions;

export default crewTasksSlice.reducer;