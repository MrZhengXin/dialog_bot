import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence


class AStarType(nn.Module):
    def __init__(self, config):
        super(AStarType, self).__init__()
        self.vocab_size = len(config.word_dict)
        self.goal_type_size = config.goal_type_size
        self.embed_size = config.embed_size
        self.hidden_size = config.hidden_size
        self.output_size = config.output_size
        self.batch_size = config.batch_size
        self.bidirectional = config.bidirectional
        self.n_layers = config.n_layers
        self.dropout_probability = config.dropout_probability
        self.device = config.device
        self.padding_idx = self.goal_type_size

        # We need to multiply some layers by two if the model is bidirectional
        self.input_size_factor = 2 if config.bidirectional else 1

        # self.text_embedding = nn.Embedding(self.vocab_size, self.embed_size)
        self.goal_embedding = nn.Embedding(self.goal_type_size + 1, self.embed_size)

        self.rnn = nn.LSTM(
            self.embed_size,
            self.hidden_size,
            self.n_layers,
            bidirectional=config.bidirectional,
        )

        self.fc1 = nn.Linear(
            self.hidden_size * self.input_size_factor + self.embed_size,
            64,
        )
        nn.init.kaiming_normal_(self.fc1.weight, mode='fan_in', nonlinearity='relu')
        self.fc2 = nn.Linear(
            64,
            self.output_size,
        )
        nn.init.kaiming_normal_(self.fc2.weight, mode='fan_in', nonlinearity='relu')
        # nn.init.xavier_uniform_(self.fc2.weight, gain=nn.init.calculate_gain('relu'))

    def init_hidden(self):
        """Set initial hidden states."""
        h0 = torch.randn(
            self.n_layers * self.input_size_factor,
            self.batch_size,
            self.hidden_size,
        )
        nn.init.orthogonal_(h0)
        c0 = torch.randn(
            self.n_layers * self.input_size_factor,
            self.batch_size,
            self.hidden_size,
        )
        nn.init.kaiming_normal_(c0, mode='fan_in', nonlinearity='relu')
        # nn.init.xavier_uniform_(c0, gain=nn.init.calculate_gain('relu'))

        h0 = h0.to(self.device)
        c0 = c0.to(self.device)

        return h0, c0

    def apply_rnn(self, embedding_out, lengths):
        packed = pack_padded_sequence(
            embedding_out,
            lengths,
            batch_first=True,
        )
        output, (hidden, cell) = self.rnn(packed, self.init_hidden()) # hidden: (num_layers * num_directions, batch, hidden_size)
        output, _ = pad_packed_sequence(output, batch_first=True)  # (batch, seq_len, bidirec*hidden)
        # output = output.permute(0, 2, 1)
        # output = F.max_pool1d(output, kernel_size=output.shape[-1]).squeeze(-1)
        # hidden = hidden.permute(1, 2, 0)
        # hidden = F.max_pool1d(hidden, kernel_size=hidden.shape[-1]).squeeze(-1)
        # hidden = hidden.view(self.n_layers, self.bidirectional, hidden.shape[1], hidden.shape[-1])[-1]
        # # (batch, bidirec*hidden)

        indices = (lengths - 1).view(-1, 1).expand(
            output.size(0), output.size(2),
        ).unsqueeze(1).to(self.device)

        output = output.gather(1, indices).squeeze(1)   # (batch, bidirec * hiddem)
        return output

    def pad_sequences(self, sequences, padding_val=0, pad_left=False):
        """Pad a list of sequences to the same length with a padding_val."""
        sequence_length = max(len(sequence) for sequence in sequences)
        if not pad_left:
            return [
                sequence + (sequence_length - len(sequence)) * [padding_val]
                for sequence in sequences
            ]
        return [
            (sequence_length - len(sequence)) * [padding_val] + sequence
            for sequence in sequences
        ]

    def forward(self, past_goal_seq, cur_goal, last_goal, tag="train"):
        if tag == "train":
            batch_size = len(past_goal_seq)
            if batch_size != self.batch_size:
                self.batch_size = batch_size

            lengths = torch.tensor([len(x) for x in past_goal_seq], dtype=torch.long)
            lengths, permutation_indices = lengths.sort(0, descending=True)

            # Pad sequences so that they are all the same length
            padded_inputs = self.pad_sequences(past_goal_seq, padding_val=self.padding_idx)
            past_goal_seq = torch.tensor(padded_inputs, dtype=torch.long)

            # Sort inputs
            past_goal_seq = past_goal_seq[permutation_indices].to(self.device)

            # Get embeddings
            text_embed = self.goal_embedding(past_goal_seq)
            output = self.apply_rnn(text_embed, lengths)
            # out = torch.relu(self.fc1(output))
            # out = torch.sigmoid(self.fc2(out))

            # cur_goal_embed = self.goal_embedding(cur_goal)[permutation_indices]
            # cur_cost_embed = torch.cat([output, cur_goal_embed], dim=-1)
            last_goal_embed = self.goal_embedding(last_goal)[permutation_indices]
            last_cost_embed = torch.cat([output, last_goal_embed], dim=-1)

            # cur_cost = F.dropout(torch.relu(self.fc1(cur_cost_embed)), 0.05)
            # cur_cost = torch.relu(self.fc1(cur_cost_embed))
            # cur_cost = torch.sigmoid(self.fc2(cur_cost))

            # remain_cost = F.dropout(torch.relu(self.fc1(last_cost_embed)), 0.05)
            remain_cost = torch.relu(self.fc1(last_cost_embed))
            remain_cost = torch.sigmoid(self.fc2(remain_cost))

            # out = 0.5 * cur_cost + 0.5 * remain_cost
            out = remain_cost
            # Put the output back in correct order
            permutation_index_pairs = list(zip(
                permutation_indices.tolist(),
                list(range(len(permutation_indices))),
            ))
            reordered_indices = [
                pair[1] for pair
                in sorted(permutation_index_pairs, key=lambda pair: pair[0])
            ]

            return out[reordered_indices]

        elif tag == "test":
            seq_embed = self.goal_embedding(past_goal_seq)
            seq_out, _ = self.rnn(seq_embed)
            seq_out = seq_out[-1]
            # out = torch.relu(self.fc1(seq_out))
            # out = torch.sigmoid(self.fc2(out))

            # cur_goal_embed = self.goal_embedding(cur_goal)
            # cur_cost_embed = torch.cat([seq_out, cur_goal_embed], dim=-1)
            # print(seq_out.shape, last_goal_embed.shape)
            last_goal_embed = self.goal_embedding(last_goal)
            last_cost_embed = torch.cat([seq_out, last_goal_embed], dim=-1)

            # cur_cost = F.dropout(torch.relu(self.fc1(cur_cost_embed)), 0.05)
            # cur_cost = torch.relu(self.fc1(cur_cost_embed))
            # cur_cost = torch.sigmoid(self.fc2(cur_cost))

            # remain_cost = F.dropout(torch.relu(self.fc1(last_cost_embed)), 0.05)
            remain_cost = torch.relu(self.fc1(last_cost_embed))
            remain_cost = torch.sigmoid(self.fc2(remain_cost))

            # out = 0.5 * cur_cost + 0.5 * remain_cost
            out = remain_cost
            return out