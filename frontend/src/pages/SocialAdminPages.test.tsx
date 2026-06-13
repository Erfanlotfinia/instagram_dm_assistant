import { render, screen } from '@testing-library/react';
import { AdminAITasksPage, AutomationRulesPage, OperatorCorrectionsPage, ScenarioCoveragePage, ScenarioSimulatorPage } from './SocialAdminPages';

test('renders scenario coverage page', () => {
  render(<ScenarioCoveragePage />);
  expect(screen.getByText('Scenario Coverage')).toBeInTheDocument();
  expect(screen.getByText('Referenced content')).toBeInTheDocument();
});

test('renders automation rules priority', () => {
  render(<AutomationRulesPage />);
  expect(screen.getByText('Structured LLM fallback')).toBeInTheDocument();
});

test('renders scenario simulator pack', () => {
  render(<ScenarioSimulatorPage />);
  expect(screen.getByText('Run scenario pack')).toBeInTheDocument();
});

test('renders admin AI tasks approval gate', () => {
  render(<AdminAITasksPage />);
  expect(screen.getByText(/requires admin approval/i)).toBeInTheDocument();
});

test('renders operator corrections', () => {
  render(<OperatorCorrectionsPage />);
  expect(screen.getByText(/Correction capture/)).toBeInTheDocument();
});
