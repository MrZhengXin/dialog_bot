import torch

from .entity.astar import AStarEntity
from .type.astar import AStarType
from .entity.config import Config as EntityConfig
from .type.config import Config as TypeConfig


class GoalPlanning:
    def __init__(self, config):
        self.goal_type = AStarType(TypeConfig())
        self.goal_entity = AStarEntity(EntityConfig())

        self.goal_type.load_state_dict(torch.load(config.goal_type_path, map_location=torch.device('cpu')))
        self.goal_entity.load_state_dict(torch.load(config.goal_entity_path, map_location=torch.device('cpu')))

    def goal_type_infer(self, past_goal_type_seq, cur_goal_type, final_goal_type):
        self.goal_type.eval()
        with torch.no_grad():
            past_goal_type_seq = torch.tensor(past_goal_type_seq, dtype=torch.long).unsqueeze(1)
            cur_goal_type = torch.tensor(cur_goal_type, dtype=torch.long).unsqueeze(0)
            final_goal_type = torch.tensor(final_goal_type, dtype=torch.long).unsqueeze(0)
            # print(final_goal_type)
            # print(past_goal_type_seq.shape, cur_goal_type.shape, final_goal_type.shape)
            output = self.goal_type(past_goal_type_seq, cur_goal_type, final_goal_type, "test")
            return output.item()

    def goal_entity_infer(self, past_entity_seq, cur_entity, final_entity):
        self.goal_entity.eval()
        with torch.no_grad():
            past_entity_seq = torch.tensor(past_entity_seq, dtype=torch.long).unsqueeze(1)
            cur_entity = torch.tensor(cur_entity, dtype=torch.long).unsqueeze(0)
            final_entity = torch.tensor(final_entity, dtype=torch.long).unsqueeze(0)
            output = self.goal_entity(past_entity_seq, cur_entity, final_entity, "test")
            return output.item()
