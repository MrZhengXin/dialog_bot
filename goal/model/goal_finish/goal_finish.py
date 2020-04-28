import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import optim
from torch.nn.utils import clip_grad_norm_
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm
from goal.model.goal_finish.lstm import RNN
from goal.model.goal_finish.config import Config
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '1'


class GoalFinishDataset(Dataset):
    def __init__(self, tag):
        path_prefix = "../../data/train/"
        self.utterance = self.file_reader(path_prefix + tag + "_binary_utterance.txt")
        self.goal_input = self.file_reader(path_prefix + tag + "_binary_goal_type.txt")
        self.final_goal_type = self.file_reader(path_prefix + tag + "_final_goal_type.txt")
        self.label = self.file_reader(path_prefix + tag + "_binary_label.txt")

    def file_reader(self, file_path):
        with open(file_path, "r", encoding='utf-8') as f:
            data = eval(f.read())
        return data

    @staticmethod
    def collate(batch):
        utterance = [item[0] for item in batch]
        goal_input = torch.tensor([item[1] for item in batch], dtype=torch.long)
        final_goal_type = torch.tensor([item[2] for item in batch], dtype=torch.long)
        target = torch.tensor([item[-1] for item in batch], dtype=torch.long)
        return utterance, goal_input, final_goal_type, target

    def __getitem__(self, i):
        return self.utterance[i], self.goal_input[i], self.final_goal_type[i], self.label[i]

    def __len__(self):
        return len(self.label)


def train_epoch(model, criterion, optimizer, scheduler, train_loader, device, max_norm):
    model.train()
    total_loss = total_acc = total = 0
    progress_bar = tqdm(train_loader, desc='Training', leave=False)
    for text, first_goal, final_goal, label in progress_bar:
        first_goal = first_goal.to(device)
        final_goal = final_goal.to(device)
        label = label.to(device)

        # Clean old gradients
        optimizer.zero_grad()

        # Forwards pass
        output = model(text, first_goal, final_goal)

        # Calculate how wrong the model is
        loss = criterion(output, label)
        prediction = output.argmax(dim=-1)
        # prediction = (output > 0.5).long()
        # Perform gradient descent, backwards pass
        loss.backward()

        clip_grad_norm_(model.rnn.parameters(), max_norm=max_norm)

        # Take a step in the right direction
        optimizer.step()
        if scheduler:
            scheduler.step()

        # Record metrics
        total_loss += loss.item()
        total_acc += (prediction == label).sum().float().item()
        total += len(label)

    return total_loss / total, total_acc / total


def validate_epoch(model, valid_loader, criterion, device):
    model.eval()
    total_loss = total_acc = total = 0
    with torch.no_grad():
        progress_bar = tqdm(valid_loader, desc='Validating', leave=False)
        for text, first_goal, final_goal, label in progress_bar:
            first_goal = first_goal.to(device)
            final_goal = final_goal.to(device)
            label = label.to(device)
            # Forwards pass
            output = model(text, first_goal, final_goal)
            # print(output.shape, label.shape)
            # break

            # Calculate how wrong the model is
            loss = criterion(output, label)
            prediction = output.argmax(dim=-1)
            # prediction = (output > 0.5).long()
            # Record metrics
            total_loss += loss.item()
            total_acc += (prediction == label).sum().float().item()
            total += len(label)

    return total_loss / total, total_acc / total


def main(config):
    train_dataset = GoalFinishDataset("train")
    valid_dataset = GoalFinishDataset("val")
    train_loader = DataLoader(train_dataset, batch_size=config.batch_size, collate_fn=train_dataset.collate, shuffle=True)
    valid_loader = DataLoader(valid_dataset, batch_size=config.batch_size, collate_fn=valid_dataset.collate, shuffle=True)
    model = RNN(config).to(config.device)
    criterion = nn.CrossEntropyLoss()
    embedding_params_ids = list(map(id, model.goal_embedding.parameters()))
    embedding_params_ids += list(map(id, model.text_embedding.parameters()))
    rest_params = filter(lambda x: id(x) not in embedding_params_ids, model.parameters())
    # optimizer = optim.Adam(
    #     [{'params': filter(lambda p: p.requires_grad, rest_params)},
    #      {'params': model.goal_embedding.parameters(), 'lr': 0.5},
    #      {'params': model.text_embedding.parameters(), 'lr': 0.5}],
    #     lr=config.lr, weight_decay=config.weight_decay
    # )
    optimizer = optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=config.lr
    )
    scheduler = CosineAnnealingLR(optimizer, 32)

    train_losses, valid_losses, min_valid_loss = [], [], float('inf')
    for epoch in range(config.num_epoch):
        train_loss, train_acc = train_epoch(model, criterion, optimizer, scheduler, train_loader, config.device, config.max_norm)
        valid_loss, valid_acc = validate_epoch(model, valid_loader, criterion, config.device)

        tqdm.write(
            f'epoch #{epoch + 1:3d}\ttrain_loss: {train_loss:.3e}'
            f' train_acc: {train_acc:.4f}'
            f' valid_loss: {valid_loss:.3e}'
            f' valid_acc: {valid_acc:.4f}\n'
        )

        # Early stop
        # if len(valid_losses) > 4 and all(valid_loss >= loss for loss in valid_losses[-5:]):
        #     print('Stopping early')
        #     break
        #
        # if valid_loss < min_valid_loss:
        #     min_valid_loss = valid_loss
        #     torch.save(model.state_dict(), config.save_path)

        train_losses.append(train_loss)
        valid_losses.append(valid_loss)


if __name__ == '__main__':
    config = Config()
    main(config)
