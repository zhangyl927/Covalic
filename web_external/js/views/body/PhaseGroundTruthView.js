covalic.views.PhaseGroundTruthView = covalic.View.extend({
    events: {
        'click .c-wizard-next-button': function () {
            this.accessWidget.once('g:accessListSaved', function () {
                covalic.router.navigate('phase/' + this.model.id +
                    '/input?wizard&curr=' + (this.wizard.current + 1) + '&total=' +
                    this.wizard.total, {trigger: true});
            }, this).saveAccessList();
        },

        'click .c-save-access-button': function () {
            this.accessWidget.once('g:accessListSaved', function () {
                girder.events.trigger('g:alert', {
                    text: 'Settings saved.',
                    type: 'success',
                    icon: 'ok',
                    timeout: 3000
                });
            }, this).saveAccessList();
        }
    },

    _saveAndGoTo: function (route) {
        this.model.once('g:saved', function () {
            covalic.router.navigate(route, {trigger: true});
        }, this).set({

        }).saveAccessList();
    },

    initialize: function (settings) {
        this.wizard = settings.wizard || false;
        this.groundTruthFolder = new girder.models.FolderModel({
            _id: this.model.get('groundTruthFolderId')
        }).once('g:fetched', function () {
            this.uploadWidget = new girder.views.UploadWidget({
                parentView: this,
                modal: false,
                parentType: 'folder',
                title: false,
                parent: this.groundTruthFolder
            });

            this.accessWidget = new girder.views.AccessWidget({
                parentView: this,
                modal: false,
                hideRecurseOption: true,
                hideSaveButton: !!this.wizard,
                modelType: 'ground truth data',
                model: this.groundTruthFolder
            });

            this.render();
        }, this).fetch();
    },

    render: function () {
        this.$el.html(covalic.templates.phaseGroundTruth({
            wizard: this.wizard,
            phase: this.model
        }));

        this.uploadWidget.setElement(this.$('.c-upload-container')).render();
        this.accessWidget.setElement(this.$('.c-access-container')).render();

        return this;
    }
});

covalic.router.route('phase/:id/groundtruth', 'phaseGroundTruth', function (id, params) {
    var phase = new covalic.models.PhaseModel({_id: id}),
        wizard = false;

    params = girder.parseQueryString(params);

    if (_.has(params, 'wizard')) {
        wizard = {
            total: window.parseInt(params.total),
            current: window.parseInt(params.curr)
        };
    }

    phase.once('g:fetched', function () {
        girder.events.trigger('g:navigateTo', covalic.views.PhaseGroundTruthView, {
            model: phase,
            wizard: wizard
        });
    }, this).on('g:error', function () {
        covalic.router.navigate('challenges', {trigger: true});
    }, this).fetch();
});
