/**
 * Clarification Widget - Interactive UI for ambiguous queries
 */
import { useState } from 'react';
import { CheckCircle2, HelpCircle } from 'lucide-react';
import type { ClarificationUI, ClarificationOption } from '../types';

interface ClarificationWidgetProps {
  clarificationUI: ClarificationUI;
  intentData: Record<string, any>;
  onSubmit: (selection: any) => void;
  disabled?: boolean;
}

export default function ClarificationWidget({
  clarificationUI,
  intentData,
  onSubmit,
  disabled = false
}: ClarificationWidgetProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [textValue, setTextValue] = useState('');

  const handleSubmit = () => {
    if (clarificationUI.ui_type === 'radio' && selectedId) {
      const selectedOption = clarificationUI.options?.find(opt => opt.id === selectedId);

      onSubmit({
        clarification_type: clarificationUI.type,
        user_selection: {
          entity_type: clarificationUI.entity_type,
          selected_id: selectedId,
          selected_label: selectedOption?.label,
          metadata: selectedOption?.metadata
        },
        original_intent: intentData
      });
    } else if (clarificationUI.ui_type === 'checkbox' && selectedIds.length > 0) {
      onSubmit({
        clarification_type: clarificationUI.type,
        user_selection: {
          entity_type: clarificationUI.entity_type,
          selected_ids: selectedIds,
          value: selectedIds
        },
        original_intent: intentData
      });
    } else if (['text', 'date', 'number'].includes(clarificationUI.ui_type) && textValue) {
      onSubmit({
        clarification_type: clarificationUI.type,
        user_selection: {
          parameter_name: clarificationUI.parameter_name,
          value: textValue,
          parameter_type: clarificationUI.parameter_type
        },
        original_intent: intentData
      });
    }
  };

  const canSubmit =
    (clarificationUI.ui_type === 'radio' && selectedId) ||
    (clarificationUI.ui_type === 'checkbox' && selectedIds.length > 0) ||
    (['text', 'date', 'number'].includes(clarificationUI.ui_type) && textValue);

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
      <div className="flex items-start gap-3 mb-4">
        <HelpCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h4 className="font-medium text-blue-900 mb-1">Clarification Needed</h4>
          <p className="text-sm text-blue-800">{clarificationUI.question}</p>
        </div>
      </div>

      <div className="space-y-2">
        {/* Radio buttons (single selection) */}
        {clarificationUI.ui_type === 'radio' && clarificationUI.options && (
          <div className="space-y-2">
            {clarificationUI.options.map((option) => (
              <OptionCard
                key={option.id}
                option={option}
                selected={selectedId === option.id}
                onSelect={() => setSelectedId(option.id)}
                disabled={disabled}
              />
            ))}
          </div>
        )}

        {/* Checkboxes (multiple selection) */}
        {clarificationUI.ui_type === 'checkbox' && clarificationUI.options && (
          <div className="space-y-2">
            {clarificationUI.options.map((option) => (
              <CheckboxOption
                key={option.id}
                option={option}
                selected={selectedIds.includes(option.id)}
                onToggle={() => {
                  setSelectedIds(prev =>
                    prev.includes(option.id)
                      ? prev.filter(id => id !== option.id)
                      : [...prev, option.id]
                  );
                }}
                disabled={disabled}
              />
            ))}
          </div>
        )}

        {/* Text input */}
        {clarificationUI.ui_type === 'text' && (
          <input
            type="text"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            placeholder={`Enter ${clarificationUI.parameter_name || 'value'}...`}
            value={textValue}
            onChange={(e) => setTextValue(e.target.value)}
            disabled={disabled}
          />
        )}

        {/* Suggestions for text input */}
        {clarificationUI.ui_type === 'text' && clarificationUI.suggestions && clarificationUI.suggestions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {clarificationUI.suggestions.map((suggestion, idx) => (
              <button
                key={idx}
                className="px-3 py-1 text-sm bg-white border border-gray-300 rounded-full hover:bg-gray-50 transition-colors"
                onClick={() => setTextValue(String(suggestion))}
                disabled={disabled}
              >
                {String(suggestion)}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Submit button */}
      <div className="mt-4 flex justify-end">
        <button
          className="btn-primary flex items-center gap-2"
          onClick={handleSubmit}
          disabled={!canSubmit || disabled}
        >
          <CheckCircle2 className="w-4 h-4" />
          Confirm Selection
        </button>
      </div>
    </div>
  );
}

interface OptionCardProps {
  option: ClarificationOption;
  selected: boolean;
  onSelect: () => void;
  disabled?: boolean;
}

function OptionCard({ option, selected, onSelect, disabled }: OptionCardProps) {
  return (
    <button
      className={`w-full text-left p-3 rounded-lg border-2 transition-all ${
        selected
          ? 'border-primary-600 bg-primary-50'
          : 'border-gray-200 bg-white hover:border-gray-300'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
      onClick={onSelect}
      disabled={disabled}
    >
      <div className="flex items-start gap-3">
        <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 mt-0.5 ${
          selected ? 'border-primary-600 bg-primary-600' : 'border-gray-300'
        }`}>
          {selected && <div className="w-2 h-2 bg-white rounded-full"></div>}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-medium text-gray-900">{option.label}</span>
            {option.recommended && (
              <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 rounded-full">
                Recommended
              </span>
            )}
          </div>
          {option.sublabel && (
            <p className="text-sm text-gray-600">{option.sublabel}</p>
          )}
          {option.relevance !== undefined && option.relevance > 0.8 && (
            <div className="mt-2 flex items-center gap-1">
              <div className="h-1.5 w-16 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-green-500 rounded-full"
                  style={{ width: `${option.relevance * 100}%` }}
                ></div>
              </div>
              <span className="text-xs text-gray-500">
                {Math.round(option.relevance * 100)}% match
              </span>
            </div>
          )}
        </div>
      </div>
    </button>
  );
}

interface CheckboxOptionProps {
  option: ClarificationOption;
  selected: boolean;
  onToggle: () => void;
  disabled?: boolean;
}

function CheckboxOption({ option, selected, onToggle, disabled }: CheckboxOptionProps) {
  return (
    <button
      className={`w-full text-left p-3 rounded-lg border-2 transition-all ${
        selected
          ? 'border-primary-600 bg-primary-50'
          : 'border-gray-200 bg-white hover:border-gray-300'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
      onClick={onToggle}
      disabled={disabled}
    >
      <div className="flex items-start gap-3">
        <div className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 mt-0.5 ${
          selected ? 'border-primary-600 bg-primary-600' : 'border-gray-300'
        }`}>
          {selected && (
            <CheckCircle2 className="w-3 h-3 text-white" />
          )}
        </div>
        <div className="flex-1">
          <span className="font-medium text-gray-900">{option.label}</span>
          {option.sublabel && (
            <p className="text-sm text-gray-600 mt-1">{option.sublabel}</p>
          )}
        </div>
      </div>
    </button>
  );
}
