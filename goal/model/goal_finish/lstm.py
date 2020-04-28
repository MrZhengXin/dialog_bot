import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence


class RNN(nn.Module):
    def __init__(self, config):
        super(RNN, self).__init__()
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
        self.padding_idx = config.word_dict["PAD"]

        # We need to multiply some layers by two if the model is bidirectional
        self.input_size_factor = 2 if config.bidirectional else 1

        self.text_embedding = nn.Embedding(self.vocab_size, self.embed_size)
        self.goal_embedding = nn.Embedding(self.goal_type_size, self.embed_size)

        self.rnn = nn.LSTM(
            self.embed_size,
            self.hidden_size,
            self.n_layers,
            bidirectional=config.bidirectional,
        )

        # attention
        self.proj = nn.Linear(
            self.embed_size,
            self.hidden_size * self.input_size_factor
        )
        nn.init.xavier_normal_(self.proj.weight)
        # output
        self.first_fc1 = nn.Linear(
            (self.hidden_size * self.input_size_factor) * 2,
            64 * 2,
        )
        nn.init.kaiming_normal_(self.first_fc1.weight, mode='fan_in', nonlinearity='relu')
        self.first_fc2 = nn.Linear(
            64 * 2,
            self.output_size,
        )
        nn.init.kaiming_normal_(self.first_fc2.weight, mode='fan_in', nonlinearity='relu')
        self.final_fc1 = nn.Linear(
            (self.hidden_size * self.input_size_factor),
            64,
        )
        nn.init.kaiming_normal_(self.final_fc1.weight, mode='fan_in', nonlinearity='relu')
        self.final_fc2 = nn.Linear(
            64,
            self.output_size,
        )
        nn.init.kaiming_normal_(self.final_fc2.weight, mode='fan_in', nonlinearity='relu')

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

        h0 = h0.to(self.device)
        c0 = c0.to(self.device)

        return h0, c0

    def apply_rnn(self, embedding_out, lengths):
        packed = pack_padded_sequence(
            embedding_out,
            lengths,
            batch_first=True,
        )
        output, _ = self.rnn(packed, self.init_hidden()) # hidden: (num_layers * num_directions, batch, hidden_size)
        output, seq_lens = pad_packed_sequence(output, batch_first=True)  # (batch, seq_len, bidirec*hidden)
        mask = torch.zeros((output.shape[:2]), dtype=torch.float)
        for i, len in enumerate(seq_lens):
            mask[i, len:] = 1.0
        mask = mask.to(output.device)

        # indices = (lengths - 1).view(-1, 1).expand(
        #     output.size(0), output.size(2),
        # ).unsqueeze(1).to(self.device)
        #
        # output = output.gather(1, indices).squeeze(1)   # (batch, bidirec * hiddem)
        return output, mask

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

    def dot_attention(self, query, key, value, mask=None):
        # query: (batch, 1, hidden)
        # key = value: (batch, hidden, seq_len)
        # mask: (batch, 1, seq_len)
        attn = torch.matmul(query, key) / query.shape[-1]
        if mask is not None:
            attn += -1e9 * mask
        weight = F.softmax(attn, dim=-1)
        value = value.permute(0, 2, 1)
        weight_memory = torch.matmul(weight, value).squeeze(1)
        return weight_memory

    def forward(self, text, first_goal, final_goal, tag="train"):
        if tag == "train":
            batch_size = len(text)
            if batch_size != self.batch_size:
                self.batch_size = batch_size

            lengths = torch.tensor([len(x) for x in text], dtype=torch.long)
            lengths, permutation_indices = lengths.sort(0, descending=True)

            # Pad sequences so that they are all the same length
            padded_inputs = self.pad_sequences(text, padding_val=self.padding_idx)
            text = torch.tensor(padded_inputs, dtype=torch.long)

            # Sort inputs
            text = text[permutation_indices].to(self.device)

            # Get embeddings
            text_embed = self.text_embedding(text)
            # text_embed = F.dropout(text_embed, self.dropout_probability)
            text_output, text_mask = self.apply_rnn(text_embed, lengths)
            text_output = text_output.permute(0, 2, 1)
            text_mask = text_mask.unsqueeze(1)

            # query: (batch, hidden)
            # key = value: (batch, seq_len, bidirec*hidden)
            # mask: (batch, seq_len)
            first_goal_embed = self.goal_embedding(first_goal[permutation_indices])  # (batch, embed_size)
            first_goal_embed = self.proj(first_goal_embed).unsqueeze(1)
            first_weight_memory = self.dot_attention(first_goal_embed, text_output, text_output, text_mask)
            # first_weight_memory = F.dropout(first_weight_memory, self.dropout_probability)
            # first_x = torch.relu(self.first_fc1(first_weight_memory))
            # first_out = torch.sigmoid(self.first_fc2(first_x))

            final_goal_embed = self.goal_embedding(final_goal[permutation_indices])  # (batch, embed_size)
            final_goal_embed = self.proj(final_goal_embed).unsqueeze(1)
            final_weight_memory = self.dot_attention(final_goal_embed, text_output, text_output, text_mask)
            # weight_memory = F.dropout(weight_memory, self.dropout_probability)
            # final_x = torch.relu(self.final_fc1(final_weight_memory))
            # final_out = torch.sigmoid(self.final_fc2(final_x))

            # out = first_out * 0.5 + final_out * 0.5

            weight_memory = torch.cat([first_weight_memory, final_weight_memory], dim=-1)
            weight_memory = F.dropout(weight_memory, self.dropout_probability)
            x = torch.relu(self.first_fc1(weight_memory))
            out = self.first_fc2(x)

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
            text_embed = self.text_embedding(text) # (seq_len, batch, embed_size)
            text_out, _ = self.rnn(text_embed)  # (seq_len, batch, direc*hidden_size)
            # print(text_out.shape)
            first_goal_embed = self.goal_embedding(first_goal) # (batch, embed_size)
            # print(first_goal_embed.shape)
            text_out = text_out.permute(1, 2, 0)
            first_goal_embed = self.proj(first_goal_embed) # (batch, direc*hidden)
            first_goal_embed = first_goal_embed.unsqueeze(1) # (batch, 1, direc*hidden)
            first_weight_memory = self.dot_attention(first_goal_embed, text_out, text_out)

            final_goal_embed = self.goal_embedding(final_goal)  # (batch, embed_size)
            final_goal_embed = self.proj(final_goal_embed).unsqueeze(1)
            final_weight_memory = self.dot_attention(final_goal_embed, text_out, text_out)
            # weight_memory = F.dropout(weight_memory, self.dropout_probability)

            weight_memory = torch.cat([first_weight_memory, final_weight_memory], dim=-1)
            weight_memory = F.dropout(weight_memory, self.dropout_probability)

            x = torch.relu(self.first_fc1(weight_memory))
            out = self.first_fc2(x)

            return out