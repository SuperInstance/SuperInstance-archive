import { EventEmitter } from 'events';
import OpenAI from 'openai';
import fs from 'fs/promises';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';

class InteractiveChatbotEditor extends EventEmitter {
    constructor(config = {}) {
        super();
        this.config = {
            openai_api_key: config.openai_api_key || process.env.OPENAI_API_KEY,
            model: config.model || 'gpt-4',
            max_conversation_history: config.max_conversation_history || 20,
            editing_sessions_directory: config.editing_sessions_directory || './data/editing_sessions',
            auto_save_interval: config.auto_save_interval || 30000, // 30 seconds
            ...config
        };

        this.openai = new OpenAI({
            apiKey: this.config.openai_api_key
        });

        this.editingSessions = new Map();
        this.conversationHistories = new Map();
        this.activeEdits = new Map();
        this.editingCommands = new Map();

        this.initializeEditingCommands();
        this.ensureDirectories();
        this.startAutoSave();
    }

    async ensureDirectories() {
        try {
            await fs.mkdir(this.config.editing_sessions_directory, { recursive: true });
        } catch (error) {
            this.emit('error', { type: 'directory-creation', error });
        }
    }

    startAutoSave() {
        setInterval(() => {
            this.autoSaveActiveSessions();
        }, this.config.auto_save_interval);
    }

    initializeEditingCommands() {
        // Define available editing commands and their handlers
        this.editingCommands.set('regenerate_segment', {
            description: 'Regenerate a specific segment of the podcast',
            parameters: ['segment_index', 'new_instructions'],
            handler: this.handleRegenerateSegment.bind(this)
        });

        this.editingCommands.set('change_tone', {
            description: 'Change the tone of a segment or entire podcast',
            parameters: ['target', 'new_tone', 'intensity'],
            handler: this.handleChangeTone.bind(this)
        });

        this.editingCommands.set('add_segment', {
            description: 'Add a new segment to the podcast',
            parameters: ['position', 'content_type', 'instructions'],
            handler: this.handleAddSegment.bind(this)
        });

        this.editingCommands.set('remove_segment', {
            description: 'Remove a segment from the podcast',
            parameters: ['segment_index', 'reason'],
            handler: this.handleRemoveSegment.bind(this)
        });

        this.editingCommands.set('adjust_dialogue', {
            description: 'Adjust dialogue between specific speakers',
            parameters: ['speakers', 'adjustment_type', 'instructions'],
            handler: this.handleAdjustDialogue.bind(this)
        });

        this.editingCommands.set('change_speaker', {
            description: 'Change which speaker delivers specific lines',
            parameters: ['segment_index', 'old_speaker', 'new_speaker', 'reason'],
            handler: this.handleChangeSpeaker.bind(this)
        });

        this.editingCommands.set('add_transition', {
            description: 'Add transitions between segments',
            parameters: ['between_segments', 'transition_type'],
            handler: this.handleAddTransition.bind(this)
        });

        this.editingCommands.set('adjust_pacing', {
            description: 'Adjust the pacing of dialogue or segments',
            parameters: ['target', 'pacing_change', 'areas_to_focus'],
            handler: this.handleAdjustPacing.bind(this)
        });

        this.editingCommands.set('enhance_content', {
            description: 'Enhance content with additional details or examples',
            parameters: ['target_area', 'enhancement_type', 'specific_requests'],
            handler: this.handleEnhanceContent.bind(this)
        });

        this.editingCommands.set('simplify_content', {
            description: 'Simplify complex content for better understanding',
            parameters: ['target_area', 'simplification_level', 'focus_areas'],
            handler: this.handleSimplifyContent.bind(this)
        });
    }

    async startEditingSession(podcastScript, sessionConfig = {}) {
        const sessionId = uuidv4();
        
        try {
            const editingSession = {
                id: sessionId,
                original_script: { ...podcastScript },
                current_script: { ...podcastScript },
                edit_history: [],
                conversation_history: [],
                created_at: new Date().toISOString(),
                last_activity: new Date().toISOString(),
                config: {
                    auto_suggestions: sessionConfig.auto_suggestions !== false,
                    context_awareness: sessionConfig.context_awareness !== false,
                    collaborative_mode: sessionConfig.collaborative_mode || false,
                    ...sessionConfig
                }
            };

            this.editingSessions.set(sessionId, editingSession);
            this.conversationHistories.set(sessionId, []);

            // Initialize conversation with system message
            const systemMessage = {
                role: 'system',
                content: this.generateSystemPrompt(podcastScript),
                timestamp: new Date().toISOString()
            };

            this.conversationHistories.get(sessionId).push(systemMessage);

            // Send welcome message
            const welcomeMessage = await this.generateWelcomeMessage(podcastScript);
            
            this.emit('editing-session-started', {
                sessionId,
                welcomeMessage,
                availableCommands: Array.from(this.editingCommands.keys())
            });

            return {
                session_id: sessionId,
                welcome_message: welcomeMessage,
                current_script: editingSession.current_script,
                available_commands: this.getAvailableCommands()
            };

        } catch (error) {
            this.emit('editing-session-start-failed', { sessionId, error });
            throw error;
        }
    }

    generateSystemPrompt(podcastScript) {
        return `You are an AI podcast editing assistant helping to refine and improve a podcast script. 

Current Podcast Details:
- Title: ${podcastScript.metadata?.title || 'Untitled'}
- Style: ${podcastScript.metadata?.style || 'Unknown'}
- Participants: ${Object.keys(podcastScript.participants || {}).join(', ')}
- Total Segments: ${podcastScript.segments?.length || 0}

Your role is to:
1. Help users edit and improve their podcast script
2. Suggest improvements for clarity, engagement, and flow
3. Execute specific editing commands
4. Maintain consistency in tone and style
5. Preserve the original intent while enhancing quality

Available editing capabilities include:
- Regenerating segments with new instructions
- Adjusting tone and pacing
- Adding/removing content
- Changing speaker assignments
- Enhancing or simplifying content
- Adding transitions

Always ask for clarification if editing requests are ambiguous. Provide specific suggestions and explain the reasoning behind recommended changes.`;
    }

    async generateWelcomeMessage(podcastScript) {
        const completion = await this.openai.chat.completions.create({
            model: this.config.model,
            messages: [
                {
                    role: 'system',
                    content: this.generateSystemPrompt(podcastScript)
                },
                {
                    role: 'user',
                    content: 'Please generate a welcoming message for the user starting their editing session, including a brief overview of what we can accomplish together and some initial suggestions for improvement.'
                }
            ],
            temperature: 0.7,
            max_tokens: 500
        });

        return completion.choices[0].message.content;
    }

    async processUserMessage(sessionId, userMessage) {
        const session = this.editingSessions.get(sessionId);
        if (!session) {
            throw new Error(`Editing session not found: ${sessionId}`);
        }

        try {
            // Add user message to conversation history
            const userMessageObj = {
                role: 'user',
                content: userMessage,
                timestamp: new Date().toISOString()
            };

            const conversationHistory = this.conversationHistories.get(sessionId);
            conversationHistory.push(userMessageObj);

            // Analyze user message to determine intent and extract commands
            const messageAnalysis = await this.analyzeUserMessage(userMessage, session);
            
            let response;
            let editResults = null;

            if (messageAnalysis.contains_editing_command) {
                // Execute editing command
                editResults = await this.executeEditingCommand(
                    sessionId,
                    messageAnalysis.command,
                    messageAnalysis.parameters
                );

                // Generate response about the edit
                response = await this.generateEditResponseMessage(
                    messageAnalysis,
                    editResults,
                    session
                );
            } else {
                // General conversation or request for suggestions
                response = await this.generateConversationalResponse(
                    sessionId,
                    userMessage,
                    session
                );
            }

            // Add assistant response to conversation history
            const assistantMessageObj = {
                role: 'assistant',
                content: response,
                timestamp: new Date().toISOString(),
                edit_results: editResults
            };

            conversationHistory.push(assistantMessageObj);

            // Trim conversation history if too long
            if (conversationHistory.length > this.config.max_conversation_history) {
                const systemMessage = conversationHistory[0];
                const recentMessages = conversationHistory.slice(-this.config.max_conversation_history + 1);
                this.conversationHistories.set(sessionId, [systemMessage, ...recentMessages]);
            }

            // Update session activity
            session.last_activity = new Date().toISOString();

            this.emit('user-message-processed', {
                sessionId,
                userMessage,
                response,
                editResults,
                messageAnalysis
            });

            return {
                response,
                edit_results: editResults,
                current_script: session.current_script,
                suggestions: messageAnalysis.auto_suggestions || []
            };

        } catch (error) {
            this.emit('message-processing-failed', { sessionId, userMessage, error });
            throw error;
        }
    }

    async analyzeUserMessage(message, session) {
        const completion = await this.openai.chat.completions.create({
            model: this.config.model,
            messages: [
                {
                    role: 'system',
                    content: `Analyze the user's message to determine if it contains editing commands and extract parameters.

Available editing commands: ${Array.from(this.editingCommands.keys()).join(', ')}

Return a JSON response with:
{
  "contains_editing_command": boolean,
  "command": "command_name" (if applicable),
  "parameters": { parameter_object } (if applicable),
  "confidence": number (0-1),
  "intent": "description of what user wants",
  "auto_suggestions": ["suggestion1", "suggestion2"] (optional)
}`
                },
                {
                    role: 'user',
                    content: `Analyze this message: "${message}"`
                }
            ],
            temperature: 0.3,
            max_tokens: 300
        });

        try {
            return JSON.parse(completion.choices[0].message.content);
        } catch (error) {
            // Fallback if JSON parsing fails
            return {
                contains_editing_command: false,
                intent: 'general_conversation',
                confidence: 0.5
            };
        }
    }

    async executeEditingCommand(sessionId, commandName, parameters) {
        const session = this.editingSessions.get(sessionId);
        const command = this.editingCommands.get(commandName);

        if (!command) {
            throw new Error(`Unknown editing command: ${commandName}`);
        }

        try {
            const editId = uuidv4();
            const editRecord = {
                id: editId,
                command: commandName,
                parameters,
                timestamp: new Date().toISOString(),
                script_before: { ...session.current_script }
            };

            // Execute the command
            const results = await command.handler(session, parameters);

            editRecord.script_after = { ...session.current_script };
            editRecord.results = results;
            editRecord.success = true;

            // Add to edit history
            session.edit_history.push(editRecord);
            
            this.emit('editing-command-executed', {
                sessionId,
                editId,
                command: commandName,
                results
            });

            return results;

        } catch (error) {
            const editRecord = {
                id: uuidv4(),
                command: commandName,
                parameters,
                timestamp: new Date().toISOString(),
                error: error.message,
                success: false
            };

            session.edit_history.push(editRecord);
            
            this.emit('editing-command-failed', {
                sessionId,
                command: commandName,
                error
            });

            throw error;
        }
    }

    async handleRegenerateSegment(session, parameters) {
        const { segment_index, new_instructions } = parameters;
        const segments = session.current_script.segments;

        if (segment_index < 0 || segment_index >= segments.length) {
            throw new Error(`Invalid segment index: ${segment_index}`);
        }

        const originalSegment = segments[segment_index];
        
        // Generate new segment content
        const completion = await this.openai.chat.completions.create({
            model: this.config.model,
            messages: [
                {
                    role: 'system',
                    content: `Regenerate a podcast segment based on new instructions while maintaining consistency with the overall script style and flow.

Original segment:
Speaker: ${originalSegment.speaker}
Content: ${originalSegment.text}

New instructions: ${new_instructions}

Return only the new segment text without speaker labels.`
                }
            ],
            temperature: 0.8,
            max_tokens: 1000
        });

        const newText = completion.choices[0].message.content.trim();
        
        // Update the segment
        segments[segment_index] = {
            ...originalSegment,
            text: newText,
            regenerated: true,
            regeneration_instructions: new_instructions,
            regenerated_at: new Date().toISOString()
        };

        return {
            segment_index,
            old_text: originalSegment.text,
            new_text: newText,
            instructions: new_instructions
        };
    }

    async handleChangeTone(session, parameters) {
        const { target, new_tone, intensity } = parameters;
        
        let targetSegments = [];
        
        if (target === 'all' || target === 'entire') {
            targetSegments = session.current_script.segments.map((_, index) => index);
        } else if (typeof target === 'number') {
            targetSegments = [target];
        } else if (Array.isArray(target)) {
            targetSegments = target;
        }

        const results = [];

        for (const segmentIndex of targetSegments) {
            const segment = session.current_script.segments[segmentIndex];
            
            const completion = await this.openai.chat.completions.create({
                model: this.config.model,
                messages: [
                    {
                        role: 'system',
                        content: `Adjust the tone of this podcast segment to be more ${new_tone} with ${intensity} intensity.

Original segment:
Speaker: ${segment.speaker}
Content: ${segment.text}

Maintain the core message and information while adjusting the tone. Return only the revised text.`
                    }
                ],
                temperature: 0.7,
                max_tokens: 1000
            });

            const newText = completion.choices[0].message.content.trim();
            
            const oldText = segment.text;
            session.current_script.segments[segmentIndex].text = newText;

            results.push({
                segment_index: segmentIndex,
                old_text: oldText,
                new_text: newText,
                tone_applied: new_tone,
                intensity: intensity
            });
        }

        return {
            target_segments: targetSegments,
            new_tone,
            intensity,
            changes: results
        };
    }

    async handleAddSegment(session, parameters) {
        const { position, content_type, instructions } = parameters;
        const segments = session.current_script.segments;

        // Generate new segment
        const completion = await this.openai.chat.completions.create({
            model: this.config.model,
            messages: [
                {
                    role: 'system',
                    content: `Create a new podcast segment based on the following requirements:
Content Type: ${content_type}
Instructions: ${instructions}

The segment should fit naturally into the existing podcast flow and style.
Determine the most appropriate speaker based on the podcast's existing participants.

Return a JSON object with:
{
  "speaker": "speaker_name",
  "text": "segment_content",
  "segment_type": "content_type"
}`
                }
            ],
            temperature: 0.8,
            max_tokens: 1000
        });

        try {
            const newSegment = JSON.parse(completion.choices[0].message.content);
            newSegment.added_at = new Date().toISOString();
            newSegment.added_instructions = instructions;

            // Insert at specified position
            const insertIndex = Math.min(position, segments.length);
            segments.splice(insertIndex, 0, newSegment);

            return {
                position: insertIndex,
                new_segment: newSegment,
                content_type,
                instructions
            };
        } catch (error) {
            throw new Error('Failed to generate new segment');
        }
    }

    async handleRemoveSegment(session, parameters) {
        const { segment_index, reason } = parameters;
        const segments = session.current_script.segments;

        if (segment_index < 0 || segment_index >= segments.length) {
            throw new Error(`Invalid segment index: ${segment_index}`);
        }

        const removedSegment = segments[segment_index];
        segments.splice(segment_index, 1);

        return {
            removed_segment: removedSegment,
            segment_index,
            reason,
            remaining_segments: segments.length
        };
    }

    async handleAdjustDialogue(session, parameters) {
        const { speakers, adjustment_type, instructions } = parameters;
        
        const targetSegments = session.current_script.segments
            .map((segment, index) => ({ segment, index }))
            .filter(({ segment }) => speakers.includes(segment.speaker));

        const results = [];

        for (const { segment, index } of targetSegments) {
            const completion = await this.openai.chat.completions.create({
                model: this.config.model,
                messages: [
                    {
                        role: 'system',
                        content: `Adjust the dialogue for ${segment.speaker} based on:
Adjustment Type: ${adjustment_type}
Instructions: ${instructions}

Original dialogue: ${segment.text}

Return only the revised dialogue.`
                    }
                ],
                temperature: 0.7,
                max_tokens: 800
            });

            const newText = completion.choices[0].message.content.trim();
            const oldText = segment.text;
            
            session.current_script.segments[index].text = newText;

            results.push({
                speaker: segment.speaker,
                segment_index: index,
                old_text: oldText,
                new_text: newText
            });
        }

        return {
            speakers,
            adjustment_type,
            instructions,
            changes: results
        };
    }

    async handleChangeSpeaker(session, parameters) {
        const { segment_index, old_speaker, new_speaker, reason } = parameters;
        const segment = session.current_script.segments[segment_index];

        if (!segment) {
            throw new Error(`Invalid segment index: ${segment_index}`);
        }

        if (segment.speaker !== old_speaker) {
            throw new Error(`Speaker mismatch: expected ${old_speaker}, found ${segment.speaker}`);
        }

        // Update speaker
        segment.speaker = new_speaker;
        segment.speaker_changed = true;
        segment.speaker_change_reason = reason;
        segment.original_speaker = old_speaker;

        return {
            segment_index,
            old_speaker,
            new_speaker,
            reason
        };
    }

    async handleAddTransition(session, parameters) {
        const { between_segments, transition_type } = parameters;
        const [fromIndex, toIndex] = between_segments;

        const completion = await this.openai.chat.completions.create({
            model: this.config.model,
            messages: [
                {
                    role: 'system',
                    content: `Create a ${transition_type} transition between these podcast segments:

From segment: ${session.current_script.segments[fromIndex]?.text || 'N/A'}
To segment: ${session.current_script.segments[toIndex]?.text || 'N/A'}

Return a JSON object with:
{
  "speaker": "appropriate_speaker",
  "text": "transition_content",
  "segment_type": "transition"
}`
                }
            ],
            temperature: 0.7,
            max_tokens: 300
        });

        try {
            const transition = JSON.parse(completion.choices[0].message.content);
            transition.is_transition = true;
            transition.transition_type = transition_type;
            transition.added_at = new Date().toISOString();

            // Insert transition between segments
            session.current_script.segments.splice(toIndex, 0, transition);

            return {
                transition,
                inserted_at: toIndex,
                between_segments,
                transition_type
            };
        } catch (error) {
            throw new Error('Failed to generate transition');
        }
    }

    async handleAdjustPacing(session, parameters) {
        const { target, pacing_change, areas_to_focus } = parameters;
        
        // Implementation for pacing adjustments
        // This would involve adding pauses, changing sentence structure, etc.
        const segments = target === 'all' ? session.current_script.segments : [session.current_script.segments[target]];
        
        const results = [];
        
        for (let i = 0; i < segments.length; i++) {
            const segment = segments[i];
            const actualIndex = target === 'all' ? i : target;
            
            const completion = await this.openai.chat.completions.create({
                model: this.config.model,
                messages: [
                    {
                        role: 'system',
                        content: `Adjust the pacing of this segment to be ${pacing_change}, focusing on: ${areas_to_focus.join(', ')}

Original: ${segment.text}

Consider adding pauses, changing sentence length, adjusting rhythm. Return only the revised text.`
                    }
                ],
                temperature: 0.6,
                max_tokens: 800
            });

            const newText = completion.choices[0].message.content.trim();
            const oldText = segment.text;
            
            session.current_script.segments[actualIndex].text = newText;

            results.push({
                segment_index: actualIndex,
                old_text: oldText,
                new_text: newText,
                pacing_change,
                focus_areas: areas_to_focus
            });
        }

        return {
            target,
            pacing_change,
            areas_to_focus,
            changes: results
        };
    }

    async handleEnhanceContent(session, parameters) {
        const { target_area, enhancement_type, specific_requests } = parameters;
        
        // Find segments related to target area
        const relevantSegments = session.current_script.segments
            .map((segment, index) => ({ segment, index }))
            .filter(({ segment }) => 
                segment.text.toLowerCase().includes(target_area.toLowerCase()) ||
                segment.segment_type === target_area
            );

        const results = [];

        for (const { segment, index } of relevantSegments) {
            const completion = await this.openai.chat.completions.create({
                model: this.config.model,
                messages: [
                    {
                        role: 'system',
                        content: `Enhance this podcast segment with ${enhancement_type}:
${specific_requests.join(', ')}

Original: ${segment.text}

Add depth, examples, or details while maintaining natural flow. Return only the enhanced text.`
                    }
                ],
                temperature: 0.7,
                max_tokens: 1200
            });

            const newText = completion.choices[0].message.content.trim();
            const oldText = segment.text;
            
            session.current_script.segments[index].text = newText;

            results.push({
                segment_index: index,
                old_text: oldText,
                new_text: newText,
                enhancement_type,
                specific_requests
            });
        }

        return {
            target_area,
            enhancement_type,
            specific_requests,
            changes: results
        };
    }

    async handleSimplifyContent(session, parameters) {
        const { target_area, simplification_level, focus_areas } = parameters;
        
        const relevantSegments = session.current_script.segments
            .map((segment, index) => ({ segment, index }))
            .filter(({ segment }) => 
                segment.text.toLowerCase().includes(target_area.toLowerCase())
            );

        const results = [];

        for (const { segment, index } of relevantSegments) {
            const completion = await this.openai.chat.completions.create({
                model: this.config.model,
                messages: [
                    {
                        role: 'system',
                        content: `Simplify this content to ${simplification_level} level, focusing on: ${focus_areas.join(', ')}

Original: ${segment.text}

Make it clearer and easier to understand while preserving key information. Return only the simplified text.`
                    }
                ],
                temperature: 0.6,
                max_tokens: 800
            });

            const newText = completion.choices[0].message.content.trim();
            const oldText = segment.text;
            
            session.current_script.segments[index].text = newText;

            results.push({
                segment_index: index,
                old_text: oldText,
                new_text: newText,
                simplification_level,
                focus_areas
            });
        }

        return {
            target_area,
            simplification_level,
            focus_areas,
            changes: results
        };
    }

    async generateEditResponseMessage(messageAnalysis, editResults, session) {
        const completion = await this.openai.chat.completions.create({
            model: this.config.model,
            messages: [
                {
                    role: 'system',
                    content: 'Generate a helpful response explaining the editing changes that were made and their impact on the podcast.'
                },
                {
                    role: 'user',
                    content: `Command executed: ${messageAnalysis.command}
Edit results: ${JSON.stringify(editResults)}

Explain what was changed and offer any additional suggestions.`
                }
            ],
            temperature: 0.7,
            max_tokens: 400
        });

        return completion.choices[0].message.content;
    }

    async generateConversationalResponse(sessionId, userMessage, session) {
        const conversationHistory = this.conversationHistories.get(sessionId);
        
        const completion = await this.openai.chat.completions.create({
            model: this.config.model,
            messages: conversationHistory.slice(-10), // Use recent conversation history
            temperature: 0.8,
            max_tokens: 500
        });

        return completion.choices[0].message.content;
    }

    getAvailableCommands() {
        return Array.from(this.editingCommands.entries()).map(([name, command]) => ({
            name,
            description: command.description,
            parameters: command.parameters
        }));
    }

    getEditingSession(sessionId) {
        return this.editingSessions.get(sessionId);
    }

    async saveEditingSession(sessionId) {
        const session = this.editingSessions.get(sessionId);
        if (!session) {
            throw new Error(`Session not found: ${sessionId}`);
        }

        const sessionPath = path.join(
            this.config.editing_sessions_directory,
            `${sessionId}.json`
        );

        const sessionData = {
            ...session,
            conversation_history: this.conversationHistories.get(sessionId)
        };

        await fs.writeFile(sessionPath, JSON.stringify(sessionData, null, 2));
        
        this.emit('session-saved', { sessionId });
        return sessionPath;
    }

    async loadEditingSession(sessionId) {
        const sessionPath = path.join(
            this.config.editing_sessions_directory,
            `${sessionId}.json`
        );

        try {
            const sessionData = JSON.parse(await fs.readFile(sessionPath, 'utf8'));
            
            this.editingSessions.set(sessionId, {
                ...sessionData,
                conversation_history: undefined // Remove from main object
            });
            
            this.conversationHistories.set(sessionId, sessionData.conversation_history || []);
            
            this.emit('session-loaded', { sessionId });
            return sessionData;
        } catch (error) {
            this.emit('session-load-failed', { sessionId, error });
            throw error;
        }
    }

    async autoSaveActiveSessions() {
        for (const sessionId of this.editingSessions.keys()) {
            try {
                await this.saveEditingSession(sessionId);
            } catch (error) {
                this.emit('auto-save-failed', { sessionId, error });
            }
        }
    }

    undoLastEdit(sessionId) {
        const session = this.editingSessions.get(sessionId);
        if (!session || session.edit_history.length === 0) {
            throw new Error('No edits to undo');
        }

        const lastEdit = session.edit_history[session.edit_history.length - 1];
        if (lastEdit.script_before) {
            session.current_script = { ...lastEdit.script_before };
            session.edit_history.pop();
            
            this.emit('edit-undone', { sessionId, undone_edit: lastEdit });
            return lastEdit;
        }
        
        throw new Error('Cannot undo: no previous script state available');
    }

    getEditHistory(sessionId) {
        const session = this.editingSessions.get(sessionId);
        return session ? session.edit_history : [];
    }

    async closeEditingSession(sessionId) {
        const session = this.editingSessions.get(sessionId);
        if (session) {
            await this.saveEditingSession(sessionId);
            this.editingSessions.delete(sessionId);
            this.conversationHistories.delete(sessionId);
            
            this.emit('session-closed', { sessionId });
        }
    }
}

export default InteractiveChatbotEditor;